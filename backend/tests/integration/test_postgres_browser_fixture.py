"""PG-049: browser fixture keeps run ownership across explicit server restarts."""

import json
from types import SimpleNamespace

import pytest
from backend.tests.support import postgres_browser_fixture as browser_fixture
from backend.tests.support.postgres_browser_fixture import (
    cleanup,
    fixture_schema,
    prepare,
    snapshot,
)
from backend.tests.support.postgres_fixtures import pg_engines as pg_engines
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError


def test_pg049_browser_fixture_reuses_only_owned_schema_and_cleans_it(
    pg_engines, tmp_path
):
    schema = prepare(tmp_path)
    try:
        before = snapshot(tmp_path)
        assert before["integrity"] == "ok"
        assert prepare(tmp_path) == schema
        assert snapshot(tmp_path) == before
        assert len(before["tables"]["registration_receipts"]["rows"]) == 1
    finally:
        cleanup(tmp_path)
    with pg_engines[0].connect() as connection:
        assert (
            connection.execute(
                text("SELECT to_regnamespace(:name)"), {"name": schema}
            ).scalar_one()
            is None
        )
        assert (
            connection.execute(
                text("SELECT to_regnamespace(:name)"), {"name": pg_engines[2]}
            ).scalar_one()
            is not None
        )


def test_pg049_browser_fixture_refuses_foreign_marker_before_connect(tmp_path):
    (tmp_path / "postgres-fixture.json").write_text(
        json.dumps(
            {
                "purpose": "medi-chat-browser",
                "database": "medi_chat_dev",
                "schema": "public",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unowned"):
        fixture_schema(tmp_path)


def test_pg049_browser_setup_failure_reclaims_its_created_schema(
    pg_engines, tmp_path, monkeypatch
):
    create = browser_fixture.create_postgres_engine
    owned = None

    def fail_owner_engine(url, **kwargs):
        nonlocal owned
        if "schema" in kwargs:
            owned = kwargs["schema"]
            raise RuntimeError("Controlled browser engine setup failure")
        return create(url, **kwargs)

    monkeypatch.setattr(browser_fixture, "create_postgres_engine", fail_owner_engine)
    try:
        with pytest.raises(RuntimeError, match="Controlled browser engine"):
            prepare(tmp_path)
        assert owned is not None
        with pg_engines[0].connect() as connection:
            exists = connection.execute(
                text("SELECT to_regnamespace(:name)"), {"name": owned}
            ).scalar_one()
        assert exists is None, (
            "Browser setup leaked its committed schema before owner-engine construction"
        )
        assert not (tmp_path / "postgres-fixture.json").exists()
    finally:
        if owned is not None:
            with pg_engines[0].begin() as connection:
                connection.execute(text(f'DROP SCHEMA IF EXISTS "{owned}" CASCADE'))


def test_pg049_browser_never_adopts_or_drops_colliding_schema(
    pg_engines, tmp_path, monkeypatch
):
    schema = pg_engines[2]
    with pg_engines[0].connect() as connection:
        before = connection.execute(text("SELECT * FROM registration_state")).all()
    monkeypatch.setattr(
        browser_fixture.uuid,
        "uuid4",
        lambda: SimpleNamespace(hex=schema.removeprefix("medi_chat_test_")),
    )
    with pytest.raises(SQLAlchemyError):
        prepare(tmp_path)
    with pg_engines[0].connect() as connection:
        assert (
            connection.execute(
                text("SELECT to_regnamespace(:name)"), {"name": schema}
            ).scalar_one()
            is not None
        )
        assert (
            connection.execute(text("SELECT * FROM registration_state")).all() == before
        )
    assert not (tmp_path / "postgres-fixture.json").exists()
