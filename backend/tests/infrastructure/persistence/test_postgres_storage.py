"""PG-004: no SQLite/path/cloud fallback in PostgreSQL settings."""

import pytest
from backend.config.database_settings import resolve_postgres_database_settings
from backend.tests.support.postgres_fixtures import validate_test_database_url


def test_pg004_explicit_local_postgres_settings() -> None:
    url = "postgresql+psycopg://test:secret@127.0.0.1:15432/medi_chat_test"
    assert (
        resolve_postgres_database_settings(database_url=url, environ={}).database_url
        == url
    )


def test_cloud_database_requires_host_allowlist_and_tls(monkeypatch):
    host = "ep-test.example.neon.tech"
    base = f"postgresql://test:secret@{host}/test"
    tls = "?sslmode=require&channel_binding=require"
    with pytest.raises(ValueError):
        resolve_postgres_database_settings(database_url=base + tls, environ={})
    env = {"MEDI_CHAT_DATABASE_HOSTS": host}
    assert (
        "sslmode=require"
        in resolve_postgres_database_settings(
            database_url=base + tls, environ=env
        ).database_url
    )
    for query in (
        "",
        "?sslmode=disable",
        "?sslmode=require",
        tls + "&host=evil.example",
        tls + "&options=-csearch_path=evil",
    ):
        with pytest.raises(ValueError):
            resolve_postgres_database_settings(database_url=base + query, environ=env)
    monkeypatch.setenv("MEDI_CHAT_DATABASE_HOSTS", host)
    from backend.infrastructure.persistence.postgres_engine import (
        create_postgres_engine,
    )

    engine = create_postgres_engine(base + tls)
    try:
        assert (
            engine.url.host == host and engine.url.query["channel_binding"] == "require"
        )
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "url",
    [
        None,
        "sqlite:///old.sqlite3",
        "bad",
        "postgresql://a:b@example.com/test",
        "postgresql://a:b@localhost/",
        "postgresql://a:b@localhost/test?host=example.com",
    ],
)
def test_pg004_invalid_settings_refused(url: str | None) -> None:
    with pytest.raises(ValueError):
        resolve_postgres_database_settings(database_url=url, environ={})


@pytest.mark.parametrize(
    "key", ["MEDI_CHAT_INDEX_PATH", "MEDI_CHAT_IMPORT_ROOT", "MEDI_CHAT_STRUCTURED_DIR"]
)
def test_pg004_legacy_runtime_paths_refused(key: str) -> None:
    with pytest.raises(ValueError):
        resolve_postgres_database_settings(
            database_url="postgresql://a:b@localhost/test", environ={key: "old"}
        )


def test_pg004_ci_host_requires_explicit_allowlist() -> None:
    url = "postgresql://a:b@postgres/test"
    with pytest.raises(ValueError):
        resolve_postgres_database_settings(database_url=url, environ={"CI": "true"})
    result = resolve_postgres_database_settings(
        database_url=url,
        environ={"CI": "true", "MEDI_CHAT_TEST_DATABASE_HOSTS": "postgres"},
    )
    assert result.database_url.startswith("postgresql+psycopg:")


def test_pg004_engine_keeps_explicit_ci_host_allowlist(monkeypatch) -> None:
    from backend.infrastructure.persistence.postgres_engine import (
        create_postgres_engine,
    )

    monkeypatch.setenv("CI", "true")
    monkeypatch.setenv("MEDI_CHAT_TEST_DATABASE_HOSTS", "postgres")
    engine = create_postgres_engine(
        "postgresql://test:secret@postgres:15432/medi_chat_test"
    )
    try:
        assert engine.url.host == "postgres"
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://medi_chat_owner:s@localhost:15432/medi_chat_dev",
        "postgresql://medi_chat_owner:s@localhost:5432/medi_chat_test",
        "postgresql://other:s@localhost:15432/medi_chat_test",
    ],
)
def test_pg049_wrong_database_profile_is_rejected_before_connection(url: str) -> None:
    with pytest.raises(ValueError):
        validate_test_database_url(url)


def test_pg004_credentials_are_not_in_settings_repr_or_validation_error(caplog) -> None:
    secret = "test_secret_do_not_log"
    settings = resolve_postgres_database_settings(
        database_url=f"postgresql://a:{secret}@localhost/test", environ={}
    )
    assert secret not in repr(settings)
    with pytest.raises(ValueError) as error:
        resolve_postgres_database_settings(
            database_url=f"postgresql://a:{secret}@example.com/test", environ={}
        )
    assert secret not in str(error.value) and secret not in caplog.text
