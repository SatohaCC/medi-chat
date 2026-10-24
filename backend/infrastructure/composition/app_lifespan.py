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
from backend.infrastructure.persistence.import_workers import ImportWorkers
from backend.infrastructure.persistence.original_document_registration import (
    OriginalDocumentRegistration,
)

from ...config.database_settings import PostgresDatabaseSettings
from ...config.generation_settings import read_generation_defaults
from ..intent.jev_classifier import JevIntentClassifier
from ..llm.provider_factory import create_llm_provider
from ..morphology.janome_keyword_extractor import JanomeKeywordExtractor
from ..morphology.keyword_extraction import get_janome_tokenizer
from ..package_insert_definitions.assembly import PackageInsertDefinitions
from ..persistence.postgres_engine import create_postgres_engine
from ..persistence.postgres_import_queries import PostgresImportQueries
from ..persistence.postgres_readiness import verify_postgres_readiness
from ..persistence.postgres_registration import PostgresRegistrationPublisher
from ..persistence.postgres_runtime import PostgresRuntime
from ..persistence.postgres_upload import (
    PostgresUploadImportReceipts,
    PostgresUploadStore,
)
from ..persistence.read_workers import ReadWorkers
from ..pmda_xml.artifact_mapping import PmdaArtifactEncoder
from ..pmda_xml.decoder import PmdaXmlDecoder
from .authentication import compose_authentication


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
                import_service = AttachmentImportCommands(
                    executor=import_executor,
                    reader=import_results,
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
