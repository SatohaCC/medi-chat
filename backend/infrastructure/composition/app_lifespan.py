"""Composition-owned PostgreSQL pool, workers and external SDK lifecycle."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any

from fastapi import FastAPI

from ...application.attachment_import.import_document import AttachmentImportService
from ...application.chat.chat_service import ChatApplicationService
from ...config.database_settings import PostgresDatabaseSettings
from ...config.generation_settings import read_generation_defaults
from ..intent.jev_classifier import JevIntentClassifier
from ..llm.provider_factory import create_llm_provider
from ..morphology.janome_keyword_extractor import JanomeKeywordExtractor
from ..morphology.keyword_extraction import get_janome_tokenizer
from ..package_insert_definitions.loader import PackageInsertDefinitions
from ..persistence.postgres_engine import create_postgres_engine
from ..persistence.postgres_readiness import verify_postgres_readiness
from ..persistence.postgres_registration import PostgresRegistrationPublisher
from ..persistence.postgres_runtime import PostgresRuntime
from ..persistence.postgres_upload import PostgresUploadStore
from ..persistence.read_workers import ReadWorkers
from ..pmda_xml.artifact_mapping import PmdaArtifactEncoder
from ..pmda_xml.decoder import PmdaXmlDecoder


class _SnapshotRequired:
    async def read_medicines(self):
        raise RuntimeError("A retrieval snapshot is required")

    async def search(self, criteria, medicines):
        raise RuntimeError("A retrieval snapshot is required")


def create_app_lifespan(
    *,
    definitions: PackageInsertDefinitions,
    settings: PostgresDatabaseSettings,
    chat_service_factory: Callable[..., Any],
    llm_provider_factory: Callable[[str | None], Any] | None = None,
    readonly_probe: bool = False,
    database_schema: str = "public",
    intent_classifier_cls: type[JevIntentClassifier] = JevIntentClassifier,
    keyword_extractor_cls: type[JanomeKeywordExtractor] = JanomeKeywordExtractor,
    janome_initializer: Callable[[], Any] = get_janome_tokenizer,
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        engine = create_postgres_engine(settings.database_url, schema=database_schema)
        workers = ReadWorkers(max_workers=4)
        classifier = None
        import_service = None
        application.state.database_engine = engine
        application.state.read_workers = workers
        try:
            await workers.run(lambda: verify_postgres_readiness(engine))
            await asyncio.to_thread(janome_initializer)
            runtime = PostgresRuntime(
                engine,
                workers=workers,
                text_search_policy=definitions.text_search_policy,
            )
            application.state.generation_runtime = runtime
            application.state.document_store = runtime
            classifier = intent_classifier_cls(
                classification_settings=definitions.jev_settings
            )
            application.state.intent_classifier = classifier
            keywords = keyword_extractor_cls(
                search_policy=definitions.text_search_policy,
                morphology_settings=definitions.morphology_settings,
            )
            required = _SnapshotRequired()
            application_service = ChatApplicationService(
                medicine_reader=required,
                evidence_reader=required,
                intent_classifier=classifier,
                keyword_extractor=keywords,
                intent_policy=definitions.intent_policy,
                answer_prompt_policy=definitions.answer_prompt_policy,
                provider_factory=llm_provider_factory or create_llm_provider,
                snapshot_provider=runtime,
            )
            application.state.chat_service = chat_service_factory(
                application_service=application_service,
                defaults=read_generation_defaults,
            )
            if not readonly_probe:
                encoder = PmdaArtifactEncoder()
                decoder = PmdaXmlDecoder(xml_settings=definitions.xml_settings)
                publisher = PostgresRegistrationPublisher(engine, encoder=encoder)
                import_service = AttachmentImportService(
                    decoder=decoder,
                    publisher=publisher,
                    upload_store=PostgresUploadStore(engine),
                )
                application.state.attachment_import_service = import_service
            yield
        finally:
            try:
                if import_service is not None:
                    await import_service.aclose()
            finally:
                try:
                    if classifier is not None:
                        await classifier.aclose()
                finally:
                    try:
                        await workers.aclose()
                    finally:
                        await asyncio.to_thread(engine.dispose)

    return lifespan
