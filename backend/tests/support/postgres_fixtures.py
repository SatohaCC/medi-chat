"""Only per-run schemas in the explicitly selected test database are owned."""

import os
import uuid
from contextlib import ExitStack, contextmanager

import pytest
from alembic import command
from alembic.config import Config
from backend.infrastructure.persistence.runtime.postgres_engine import (
    create_postgres_engine,
)
from backend.tests.support.paths import BACKEND_ROOT
from sqlalchemy import text
from sqlalchemy.engine import make_url


def validate_test_database_url(value: str, *, runtime: bool = False) -> None:
    url = make_url(value)
    expected_role = "medi_chat_app" if runtime else "medi_chat_owner"
    if (
        url.host not in {"127.0.0.1", "localhost", "::1"}
        or url.port != 15432
        or url.database != "medi_chat_test"
        or url.username != expected_role
        or url.query
    ):
        raise ValueError(
            "Refusing PostgreSQL tests outside the explicitly owned local test database and role"
        )


@contextmanager
def owned_postgres_engines():
    owner_url = os.environ.get("TEST_DATABASE_URL")
    runtime_url = os.environ.get("TEST_RUNTIME_DATABASE_URL")
    if not owner_url or not runtime_url:
        pytest.fail(
            "Explicit TEST_DATABASE_URL and TEST_RUNTIME_DATABASE_URL are required for real PostgreSQL tests"
        )
    validate_test_database_url(owner_url)
    validate_test_database_url(runtime_url, runtime=True)
    schema = "medi_chat_test_" + uuid.uuid4().hex
    with ExitStack() as cleanup:
        admin = create_postgres_engine(owner_url)
        cleanup.callback(admin.dispose)
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(
                text(f'GRANT USAGE ON SCHEMA "{schema}" TO medi_chat_app')
            )
            connection.execute(
                text(
                    f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema}" GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO medi_chat_app'
                )
            )

        def drop_owned_schema():
            with admin.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))

        # Register only after our CREATE/GRANT transaction committed successfully.
        # Later engine/migration errors must release this exact owned namespace.
        cleanup.callback(drop_owned_schema)
        owner = create_postgres_engine(owner_url, schema=schema)
        cleanup.callback(owner.dispose)
        runtime = create_postgres_engine(runtime_url, schema=schema)
        cleanup.callback(runtime.dispose)
        with owner.begin() as connection:
            config = Config(str(BACKEND_ROOT / "postgres-alembic.ini"))
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        yield owner, runtime, schema


@pytest.fixture
def pg_engines():
    with owned_postgres_engines() as engines:
        yield engines


@pytest.fixture
def pg_api(pg_engines, monkeypatch):
    """Same hand-authored REST/WS corpus as the former prepared-index fixture."""
    from backend.infrastructure.persistence.registration.postgres_registration_publisher import (
        PostgresRegistrationPublisher,
    )
    from backend.infrastructure.pmda_xml.pmda_artifact_encoder import (
        PmdaArtifactEncoder,
    )
    from backend.infrastructure.pmda_xml.pmda_xml_decoder import PmdaXmlDecoder
    from backend.tests.support.attachment_import_fixtures import xml_source

    raw = xml_source(
        "<AdverseEvents><Detail><Lang>頭痛に注意してください。記載0 頭痛に注意してください。記載1 頭痛に注意してください。記載2</Lang></Detail></AdverseEvents>"
    )
    raw = (
        raw.replace(b"000001", b"test")
        .replace(
            b"<PackageInsertNo>test</PackageInsertNo>",
            b"<PackageInsertNo>001</PackageInsertNo>",
        )
        .replace(b"111111111111", b"1234567A0000")
        .replace("製品A".encode(), "テスト薬".encode())
        .replace(
            b"</ApprovalEtc>",
            "</ApprovalEtc><GenericName><Lang>テスト成分</Lang></GenericName>".encode(),
        )
    )
    PostgresRegistrationPublisher(pg_engines[0], encoder=PmdaArtifactEncoder()).publish(
        PmdaXmlDecoder().decode(raw), raw
    )
    for key in (
        "TYPESAFE_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
    ):
        monkeypatch.setenv(key, "")
    monkeypatch.setenv(
        "MEDI_CHAT_DATABASE_URL", os.environ["TEST_RUNTIME_DATABASE_URL"]
    )
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    from backend.main import create_app

    def build(**kwargs):
        from backend.tests.support.authentication import SignedTestActor

        app = create_app(
            database_url=os.environ["TEST_RUNTIME_DATABASE_URL"],
            _database_schema=pg_engines[2],
            **kwargs,
        )
        app.add_middleware(SignedTestActor)
        return app

    return build
