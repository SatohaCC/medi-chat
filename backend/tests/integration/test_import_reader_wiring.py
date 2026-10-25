"""IH-020: PostgreSQL HTTP fixtures wire Query and replay ports separately."""

import importlib
import inspect

import pytest
from backend.infrastructure.persistence.queries.postgres_import_query_reader import (
    PostgresImportQueries,
)
from backend.infrastructure.persistence.registration.postgres_registration_publisher import (
    PostgresRegistrationPublisher,
)
from backend.infrastructure.pmda_xml.pmda_artifact_encoder import PmdaArtifactEncoder
from fastapi import FastAPI
from sqlalchemy import create_engine


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "module_name,fixture_name",
    [
        ("backend.tests.integration.test_postgres_registration", "pg_client"),
        ("backend.tests.presentation.test_attachment_import_http", "client"),
        ("backend.tests.presentation.test_registration_http", "client"),
    ],
)
async def test_http_fixture_query_and_replay_readers_are_separate(
    monkeypatch, module_name, fixture_name
):
    # Construct real adapters; creating the engine/HTTP fixture performs no DB I/O.
    engine = create_engine("postgresql+psycopg://unused@127.0.0.1:1/unused")
    publisher = PostgresRegistrationPublisher(engine, encoder=PmdaArtifactEncoder())
    module = importlib.import_module(module_name)
    app = FastAPI()
    monkeypatch.setattr(module, "FastAPI", lambda: app)
    fixture = inspect.unwrap(getattr(module, fixture_name))(publisher)
    try:
        await anext(fixture)
        command = app.state.attachment_import_service
        query = app.state.attachment_import_queries
        assert command.reader is publisher.results
        assert isinstance(query.reader, PostgresImportQueries)
        assert query.reader.engine is publisher.engine
        inspect.signature(query.reader.read_result).bind("000001_test", "a" * 64)
        inspect.signature(command.reader.replay_result).bind("000001_test", "a" * 64)
    finally:
        await fixture.aclose()
        engine.dispose()
