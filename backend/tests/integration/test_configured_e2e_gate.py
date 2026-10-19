"""PG-048: configured DB is never repaired/replaced; only owned probe stops."""

import os
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

import pytest
from backend.config.database_settings import (
    PostgresDatabaseSettings,
    resolve_postgres_database_settings,
)
from backend.config.runtime_environment import load_runtime_environment
from backend.infrastructure.cli.configured_e2e_gate import run_gate, selected_settings
from backend.tests.integration.test_postgres_registration import (
    pg_publisher as pg_publisher,
)
from backend.tests.integration.test_postgres_registration import publish
from backend.tests.support.postgres_fixtures import pg_engines as pg_engines
from backend.tests.support.registration_oracles import source
from sqlalchemy import text


def settings():
    return PostgresDatabaseSettings(os.environ["TEST_RUNTIME_DATABASE_URL"])


def snapshot(engine):
    with engine.connect() as connection:
        names = (
            connection.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname=current_schema() ORDER BY tablename"
                )
            )
            .scalars()
            .all()
        )
        return tuple(
            (
                name,
                connection.execute(
                    text(
                        f"SELECT md5(COALESCE(string_agg(value, chr(10) ORDER BY value),'')) FROM (SELECT to_jsonb(t)::text value FROM \"{name}\" t) q"
                    )
                ).scalar_one(),
            )
            for name in names
        )


@pytest.mark.parametrize("condition", ["unmanaged", "missing_table"])
def test_unprepared_configured_database_is_not_repaired(
    pg_engines, pg_publisher, condition
):
    publish(pg_publisher, source("テストconfigured"))
    with pg_engines[0].begin() as connection:
        connection.execute(
            text(
                "DROP TABLE alembic_version"
                if condition == "unmanaged"
                else "DROP TABLE search_units"
            )
        )
    before = snapshot(pg_engines[0])
    with pytest.raises(RuntimeError, match="schema_not_ready"):
        run_gate(settings(), schema=pg_engines[2])
    assert snapshot(pg_engines[0]) == before


def test_normal_runtime_loading_and_gate_resolve_same_database_from_other_cwd(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    load_runtime_environment()
    assert selected_settings() == resolve_postgres_database_settings()
    assert "***" not in selected_settings().database_url


def test_failed_os_health_stops_only_the_spawned_process(
    pg_engines, pg_publisher, monkeypatch
):
    publish(pg_publisher, source("テストconfigured"))
    original = subprocess.Popen
    owned = []

    def spawn_unhealthy(command, **kwargs):
        if command[0] == "taskkill":
            return original(command, **kwargs)
        child = original(
            [sys.executable, "-m", "http.server", "3215", "--bind", "127.0.0.1"],
            **kwargs,
        )
        owned.append(child)
        return child

    monkeypatch.setattr(subprocess, "Popen", spawn_unhealthy)
    with pytest.raises(RuntimeError, match="health timed out"):
        run_gate(settings(), schema=pg_engines[2], port=3215, timeout=0.5)
    assert len(owned) == 1 and owned[0].poll() is not None
    with socket.socket() as stopped:
        assert stopped.connect_ex(("127.0.0.1", 3215)) != 0


def test_real_sentinel_process_survives_occupied_probe(pg_engines, pg_publisher):
    publish(pg_publisher, source("テストconfigured"))
    sentinel = subprocess.Popen(
        [sys.executable, "-m", "http.server", "3214", "--bind", "127.0.0.1"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(50):
            try:
                with urlopen("http://127.0.0.1:3214", timeout=1) as response:
                    assert response.status == 200
                break
            except OSError:
                time.sleep(0.1)
        else:
            pytest.fail("Owned sentinel did not start")
        with pytest.raises(RuntimeError, match="occupied"):
            run_gate(settings(), schema=pg_engines[2], port=3214)
        assert sentinel.poll() is None
    finally:
        sentinel.terminate()
        sentinel.wait(timeout=10)


def test_missing_configured_publication_fails_without_creating_it(pg_engines):
    before = snapshot(pg_engines[0])
    with pytest.raises(RuntimeError, match="initial_registration_required"):
        run_gate(settings(), schema=pg_engines[2])
    assert snapshot(pg_engines[0]) == before


def test_configured_corruption_is_not_replaced_by_fresh_success(
    pg_engines, pg_publisher
):
    publish(pg_publisher, source("テストconfigured"))
    with pg_engines[0].begin() as connection:
        connection.execute(text("UPDATE search_units SET query_text='破損'"))
    before = snapshot(pg_engines[0])
    with pytest.raises(RuntimeError, match="payload_integrity_invalid"):
        run_gate(settings(), schema=pg_engines[2])
    assert snapshot(pg_engines[0]) == before


def test_occupied_port_is_not_taken_over(pg_engines, pg_publisher):
    publish(pg_publisher, source("テストconfigured"))
    with socket.socket() as sentinel:
        sentinel.bind(("127.0.0.1", 0))
        sentinel.listen()
        port = sentinel.getsockname()[1]
        with pytest.raises(RuntimeError, match="occupied"):
            run_gate(settings(), schema=pg_engines[2], port=port)
        assert sentinel.getsockname()[1] == port


def test_pg048_actual_configured_probe_reads_only_health(pg_engines, pg_publisher):
    receipt = publish(pg_publisher, source("テストconfigured"))
    before = snapshot(pg_engines[0])
    result = run_gate(settings(), schema=pg_engines[2], port=3216)
    assert result["os_health"]["generation_id"] == receipt.generation_id
    assert snapshot(pg_engines[0]) == before
