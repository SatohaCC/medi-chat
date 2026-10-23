"""PG-049: setup exceptions reclaim only the schema this fixture created."""

import os
import re
import uuid
from types import SimpleNamespace

import pytest
from backend.tests.support import postgres_fixtures
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

pytestmark = pytest.mark.postgres


def test_pg049_owned_schema_is_reclaimed_when_engine_setup_fails(monkeypatch):
    postgres_fixtures.validate_test_database_url(os.environ["TEST_DATABASE_URL"])
    create = postgres_fixtures.create_postgres_engine
    observer = create(os.environ["TEST_DATABASE_URL"])
    owned = None
    calls = 0

    def fail_after_schema_creation(url, **kwargs):
        nonlocal calls, owned
        calls += 1
        if calls == 2:
            owned = kwargs["schema"]
            raise RuntimeError("Controlled owner engine setup failure")
        return create(url, **kwargs)

    monkeypatch.setattr(
        postgres_fixtures, "create_postgres_engine", fail_after_schema_creation
    )
    try:
        with (
            pytest.raises(RuntimeError, match="Controlled owner engine"),
            postgres_fixtures.owned_postgres_engines(),
        ):
            raise AssertionError("Fixture setup unexpectedly succeeded")
        assert owned is not None
        with observer.connect() as connection:
            exists = connection.execute(
                text("SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname=:schema)"),
                {"schema": owned},
            ).scalar_one()
        assert not exists, "Fixture leaked its committed schema after setup failed"
    finally:
        if owned is not None:
            assert re.fullmatch(r"medi_chat_test_[0-9a-f]{32}", owned)
            with observer.begin() as connection:
                connection.execute(text(f'DROP SCHEMA IF EXISTS "{owned}" CASCADE'))
        observer.dispose()


def test_pg049_fixture_never_drops_a_colliding_preexisting_schema(monkeypatch):
    postgres_fixtures.validate_test_database_url(os.environ["TEST_DATABASE_URL"])
    observer = postgres_fixtures.create_postgres_engine(os.environ["TEST_DATABASE_URL"])
    identity = uuid.uuid4().hex
    sentinel = "medi_chat_test_" + identity
    with observer.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{sentinel}"'))
        connection.execute(text(f'CREATE TABLE "{sentinel}".sentinel (value text)'))
        connection.execute(
            text(f"INSERT INTO \"{sentinel}\".sentinel VALUES ('テスト別所有schema')")
        )
    monkeypatch.setattr(
        postgres_fixtures.uuid, "uuid4", lambda: SimpleNamespace(hex=identity)
    )
    try:
        with pytest.raises(SQLAlchemyError), postgres_fixtures.owned_postgres_engines():
            raise AssertionError("A preexisting schema must not be adopted")
        with observer.connect() as connection:
            assert (
                connection.execute(
                    text(f'SELECT value FROM "{sentinel}".sentinel')
                ).scalar_one()
                == "テスト別所有schema"
            )
    finally:
        with observer.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{sentinel}" CASCADE'))
        observer.dispose()
