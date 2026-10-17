"""FastAPI lifespan用のInfrastructure具象アダプタ組み立てと破棄。"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI

from ...application.attachment_import.import_document import AttachmentImportService
from ...application.medicine.suggestions import MedicineSuggester
from ...config.database_settings import DatabaseSettings
from ...config.generation_settings import read_generation_defaults
from ...config.import_settings import resolve_import_directory
from ..intent.jev_classifier import JevIntentClassifier
from ..llm.provider_factory import create_llm_provider
from ..morphology.janome_keyword_extractor import JanomeKeywordExtractor
from ..morphology.keyword_extraction import get_janome_tokenizer
from ..package_insert_definitions.loader import PackageInsertDefinitions
from ..persistence.attachment_import_store import FileAttachmentImportStore
from ..persistence.evidence_reader import SqlAlchemyEvidenceReader
from ..persistence.generation_runtime import GenerationRuntime
from ..persistence.index_reader import SqlAlchemyIndexReader
from ..persistence.medicine_reader import SqlAlchemyMedicineReader
from ..persistence.read_workers import ReadWorkers
from ..persistence.readonly_engine import create_readonly_engine
from ..persistence.registration_publisher import SqliteRegistrationPublisher
from ..persistence.sqlite_engine import create_sqlite_engine
from ..persistence.sqlite_recovery import recover_sqlite_journal
from ..pmda_xml.artifact_mapping import PmdaArtifactEncoder
from ..pmda_xml.decoder import PmdaXmlDecoder
from .index_verifier import verify_index_readiness
from .recovery_readiness import ReadOnlyGenerationProbe, verify_no_recovery_work


def create_app_lifespan(
    *,
    definitions: PackageInsertDefinitions,
    settings: DatabaseSettings,
    chat_service_factory: Callable[..., Any],
    llm_provider_factory: Callable[[str | None], Any] | None = None,
    import_directory: Path | None = None,
    readonly_probe: bool = False,
    intent_classifier_cls: type[JevIntentClassifier] = JevIntentClassifier,
    keyword_extractor_cls: type[JanomeKeywordExtractor] = JanomeKeywordExtractor,
    publisher_cls: type[SqliteRegistrationPublisher] = SqliteRegistrationPublisher,
    janome_initializer: Callable[[], Any] = get_janome_tokenizer,
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    """FastAPI アプリケーションの lifespan コンテキストマネージャを生成する。"""

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        if readonly_probe:
            await asyncio.to_thread(verify_no_recovery_work, settings.index_path)
        else:
            await asyncio.to_thread(recover_sqlite_journal, settings.index_path)
        await asyncio.to_thread(
            verify_index_readiness, settings.structured_dir, settings.index_path
        )
        await asyncio.to_thread(janome_initializer)
        engine = create_readonly_engine(settings.index_path)
        workers = ReadWorkers(max_workers=4)
        application.state.index_engine = engine
        application.state.read_workers = workers

        index_reader = SqlAlchemyIndexReader(engine, workers=workers)
        medicine_reader = SqlAlchemyMedicineReader(engine, workers=workers)
        evidence_reader = SqlAlchemyEvidenceReader(
            engine, workers=workers, text_search_policy=definitions.text_search_policy
        )
        application.state.index_reader = index_reader
        application.state.medicine_reader = medicine_reader
        application.state.evidence_reader = evidence_reader

        medicines = await medicine_reader.read_medicines()
        application.state.medicine_suggester = (
            MedicineSuggester.from_registered_medicines(medicines)
        )

        stats = await index_reader.read_index_stats()
        application.state.document_store = SimpleNamespace(
            index_stats=stats,
            get_document=index_reader.get_document,
            medicines=medicines,
        )

        intent_classifier = intent_classifier_cls(
            classification_settings=definitions.jev_settings
        )
        keyword_extractor = keyword_extractor_cls(
            search_policy=definitions.text_search_policy,
            morphology_settings=definitions.morphology_settings,
        )
        application.state.chat_service = chat_service_factory(
            medicine_reader=medicine_reader,
            evidence_reader=evidence_reader,
            intent_classifier=intent_classifier,
            keyword_extractor=keyword_extractor,
            intent_policy=definitions.intent_policy,
            answer_prompt_policy=definitions.answer_prompt_policy,
            provider_factory=llm_provider_factory or create_llm_provider,
            defaults=read_generation_defaults,
        )
        registration_engine = None
        try:
            if readonly_probe:
                application.state.generation_runtime = ReadOnlyGenerationProbe(
                    settings.index_path, workers
                )
                yield
                return
            store = await asyncio.to_thread(
                FileAttachmentImportStore,
                import_directory or resolve_import_directory(),
            )
            registration_engine = create_sqlite_engine(settings.database_url)
            decoder = PmdaXmlDecoder(xml_settings=definitions.xml_settings)
            encoder = PmdaArtifactEncoder()
            publisher = publisher_cls(
                settings.index_path,
                store,
                xml_settings=definitions.xml_settings,
                decoder=decoder,
                encoder=encoder,
                engine=registration_engine,
                allowed_roots=(
                    settings.structured_dir,
                    settings.structured_dir.parent / "originals",
                ),
            )
            import_service = AttachmentImportService(
                decoder=decoder,
                encoder=encoder,
                store=store,
                publisher=publisher,
            )
            application.state.attachment_import_service = import_service
            try:
                await workers.run(publisher.recover)
                runtime = GenerationRuntime(
                    publisher,
                    workers=workers,
                    text_search_policy=definitions.text_search_policy,
                    xml_settings=definitions.xml_settings,
                    decoder=decoder,
                )
                application.state.generation_runtime = runtime
                application.state.chat_service.snapshot_provider = runtime
                await runtime.warmup()
                yield
            finally:
                await import_service.aclose()
        finally:
            try:
                await intent_classifier.aclose()
            finally:
                try:
                    await workers.aclose()
                finally:
                    try:
                        if registration_engine is not None:
                            await asyncio.to_thread(registration_engine.dispose)
                    finally:
                        await asyncio.to_thread(engine.dispose)

    return lifespan
