"""PG-010/034/035: real DB readiness, never startup DDL or XML fallback."""

import copy

import pytest
from backend.infrastructure.persistence.registration.registration_payloads import (
    FigureInput,
    PostgresRegistrationInput,
)
from backend.infrastructure.persistence.runtime.postgres_readiness import (
    verify_postgres_readiness,
)
from backend.infrastructure.persistence.schemas import attachment_tables as s
from backend.infrastructure.pmda_xml.pmda_xml_decoder import PmdaXmlDecoder
from backend.tests.integration.test_postgres_registration import (
    pg_publisher as pg_publisher,
)
from backend.tests.integration.test_postgres_registration import publish
from backend.tests.support.postgres_fixtures import pg_engines as pg_engines
from backend.tests.support.registration_oracles import source
from sqlalchemy import event, select, text, update


def test_pg035_empty_publication_requires_explicit_initialization(pg_engines):
    with pytest.raises(RuntimeError, match="initial_registration_required"):
        verify_postgres_readiness(pg_engines[1])
    with pg_engines[0].connect() as connection:
        assert connection.execute(select(s.state.c.generation_id)).scalar_one() is None


def test_pg034_035_prepared_readiness_has_no_ddl_original_or_structure_transfer(
    pg_engines, pg_publisher
):
    publish(pg_publisher, source("テスト準備状態"))
    statements = []

    def observe(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement.lower())

    event.listen(pg_engines[1], "before_cursor_execute", observe)
    try:
        verify_postgres_readiness(pg_engines[1])
        assert statements
        assert not any(
            value.lstrip().startswith(
                ("insert", "update", "delete", "create", "alter", "drop")
            )
            for value in statements
        )
        assert not any(
            "attachment_versions.source" in value
            or "attachment_assets.content" in value
            for value in statements
        )
        assert not any(
            "select attachment_versions.structure" in value for value in statements
        )
    finally:
        event.remove(pg_engines[1], "before_cursor_execute", observe)


@pytest.mark.parametrize(
    "corruption", ["schema", "transformer", "missing", "invariant", "reference"]
)
def test_pg010_readiness_refuses_stored_structure_corruption(
    pg_engines, pg_publisher, corruption
):
    publish(pg_publisher, source("テスト破損拒否"))
    with pg_engines[0].begin() as connection:
        value = copy.deepcopy(
            connection.execute(select(s.versions.c.structure)).scalar_one()
        )
        if corruption == "schema":
            value["schema_version"] = 999
        elif corruption == "transformer":
            value["transformer_version"] = "unsupported"
        elif corruption == "missing":
            del value["document"]["document_id"]
        elif corruption == "invariant":
            value["document"]["document_id"] = ""
        else:
            value["document"]["sections"][0]["body"]["blocks"][0]["references"] = [
                {"target_id": "missing", "label": "テスト参照", "metadata": {}}
            ]
        connection.execute(update(s.versions).values(structure=value))
    with pytest.raises(RuntimeError, match="stored_structure_invalid"):
        verify_postgres_readiness(pg_engines[1])


def test_pg035_revision_and_pointer_corruption_refused(pg_engines, pg_publisher):
    publish(pg_publisher, source("テスト公開pointer"))
    with pg_engines[0].begin() as connection:
        connection.execute(text("UPDATE alembic_version SET version_num='unknown'"))
    with pytest.raises(RuntimeError, match="schema_not_ready"):
        verify_postgres_readiness(pg_engines[1])


def assert_database_details_private(message, url):
    for value in (
        url.username,
        url.password,
        url.host,
        url.database,
        url.render_as_string(hide_password=False),
    ):
        if value and value in message:
            raise AssertionError("Database connection details were exposed")


def test_pg004_035_runtime_select_permission_failure_is_private(
    pg_engines, pg_publisher
):
    publish(pg_publisher, source("テスト権限拒否"))
    with pg_engines[0].begin() as connection:
        connection.execute(
            text("REVOKE SELECT ON registration_state FROM medi_chat_app")
        )
    with pytest.raises(RuntimeError, match="schema_not_ready") as error:
        verify_postgres_readiness(pg_engines[1])
    assert_database_details_private(str(error.value), pg_engines[1].url)
    assert "postgresql://" not in str(error.value).lower()
    assert "postgresql+psycopg://" not in str(error.value).lower()
    assert "SELECT" not in str(error.value)
    assert pg_engines[1].pool.checkedout() == 0


def test_pg004_035_unavailable_connection_is_private_and_has_no_fallback(pg_engines):
    import socket

    from backend.infrastructure.persistence.runtime.postgres_engine import (
        create_postgres_engine,
    )

    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
        canary_url = pg_engines[1].url.set(
            port=port,
            username="test_canary_role",
            password="test_canary_password",
            database="test_canary_database",
        )
        engine = create_postgres_engine(
            canary_url.render_as_string(hide_password=False),
            schema=pg_engines[2],
        )
        try:
            with pytest.raises(RuntimeError, match="schema_not_ready") as error:
                verify_postgres_readiness(engine)
            assert_database_details_private(str(error.value), canary_url)
            assert "postgresql://" not in str(error.value).lower()
            assert "postgresql+psycopg://" not in str(error.value).lower()
            from sqlalchemy.pool import QueuePool

            assert isinstance(engine.pool, QueuePool)
            assert engine.pool.checkedout() == 0
        finally:
            engine.dispose()


@pytest.mark.parametrize(
    "corruption", ["source", "figure", "unit", "product_sections", "active"]
)
def test_pg035_readiness_detects_db_payload_and_publication_damage(
    pg_engines, pg_publisher, corruption
):
    raw = source("テストDB整合性")
    pg_publisher.publish_inputs(
        (
            PostgresRegistrationInput(
                PmdaXmlDecoder().decode(raw),
                raw,
                (FigureInput("test.gif", "image/gif", b"GIF89a"),),
            ),
        )
    )
    with pg_engines[0].begin() as connection:
        if corruption == "source":
            connection.execute(update(s.versions).values(source=b"x" * len(raw)))
        elif corruption == "figure":
            connection.execute(update(s.assets).values(content=b"BAD89a"))
        elif corruption == "unit":
            connection.execute(update(s.units).values(query_text="破損投影"))
        elif corruption == "product_sections":
            connection.execute(s.unit_products.delete())
        else:
            connection.execute(s.active.delete())
    with pytest.raises(
        RuntimeError, match="(?:payload_integrity_invalid|publication_state_invalid)"
    ):
        verify_postgres_readiness(pg_engines[1])
