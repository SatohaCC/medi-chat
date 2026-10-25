"""Composition-owned PostgreSQL pool, workers and external SDK lifecycle."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any

from fastapi import FastAPI

from backend.application.attachment_import.commands.import_documents import (
    AttachmentImportCommands,
)
from backend.application.attachment_import.queries.import_history import (
    ImportHistoryQueries,
)
from backend.application.chat.queries.chat import (
    ChatQueries,
)
from backend.config.database_settings import PostgresDatabaseSettings
from backend.config.generation_settings import read_generation_defaults
from backend.infrastructure.composition.authentication_composition import (
    compose_authentication,
)
from backend.infrastructure.document_import.original_document_registration_adapter import (
    OriginalDocumentRegistration,
)
from backend.infrastructure.intent.jev_classifier import JevIntentClassifier
from backend.infrastructure.llm.llm_provider_factory import create_llm_provider
from backend.infrastructure.morphology.janome_keyword_extraction import (
    get_janome_tokenizer,
)
from backend.infrastructure.morphology.janome_keyword_extractor import (
    JanomeKeywordExtractor,
)
from backend.infrastructure.package_insert_definitions.definition_assembly import (
    PackageInsertDefinitions,
)
from backend.infrastructure.persistence.queries.postgres_import_query_reader import (
    PostgresImportQueries,
)
from backend.infrastructure.persistence.queries.postgres_search_snapshot_provider import (
    PostgresRuntime,
)
from backend.infrastructure.persistence.registration.postgres_import_replay_reader import (
    PostgresImportReplayReader,
)
from backend.infrastructure.persistence.registration.postgres_registration_publisher import (
    PostgresRegistrationPublisher,
)
from backend.infrastructure.persistence.runtime.import_workers import ImportWorkers
from backend.infrastructure.persistence.runtime.postgres_engine import (
    create_postgres_engine,
)
from backend.infrastructure.persistence.runtime.postgres_readiness import (
    verify_postgres_readiness,
)
from backend.infrastructure.persistence.runtime.read_workers import ReadWorkers
from backend.infrastructure.persistence.stores.postgres_upload_store import (
    PostgresUploadImportReceipts,
    PostgresUploadStore,
)
from backend.infrastructure.pmda_xml.pmda_artifact_encoder import PmdaArtifactEncoder
from backend.infrastructure.pmda_xml.pmda_xml_decoder import PmdaXmlDecoder


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
            application.state.authentication = await asyncio.to_thread(
                compose_authentication, engine
            )
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
            application_service = ChatQueries(
                intent_classifier=classifier,
                keyword_extractor=keywords,
                intent_policy=definitions.intent_policy,
                retrieval_policy=definitions.retrieval_policy,
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
                import_executor = ImportWorkers()
                import_results = PostgresImportQueries(engine)
                replay_reader = PostgresImportReplayReader(engine)
                import_service = AttachmentImportCommands(
                    executor=import_executor,
                    reader=replay_reader,
                    upload_store=PostgresUploadStore(engine),
                    upload_receipts=PostgresUploadImportReceipts(engine),
                    registration=OriginalDocumentRegistration(
                        decoder=decoder, publisher=publisher
                    ),
                )
                application.state.attachment_import_service = import_service
                application.state.attachment_import_queries = ImportHistoryQueries(
                    reader=import_results,
                    executor=import_executor,
                )
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
