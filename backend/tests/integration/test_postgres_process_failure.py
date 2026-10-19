"""PG-018/038/048: actual owned OS failure and cross-process publication."""

import base64
import json
import os
import subprocess
import sys
import time

import pytest
from backend.infrastructure.persistence import postgres_schema as schema
from backend.infrastructure.persistence.postgres_readiness import (
    verify_postgres_readiness,
)
from backend.infrastructure.persistence.postgres_registration import (
    FigureInput,
    PostgresRegistrationInput,
)
from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder
from backend.tests.application.indexing.test_active_attachment_projection import (
    mixed_source,
)
from backend.tests.integration.test_postgres_registration import (
    pg_publisher as pg_publisher,
)
from backend.tests.integration.test_postgres_registration import publish
from backend.tests.support.generation_os_server import main_server
from backend.tests.support.paths import PROJECT_ROOT
from backend.tests.support.postgres_fixtures import pg_engines as pg_engines
from backend.tests.support.postgres_observations import digest
from backend.tests.support.registration_oracles import source
from sqlalchemy import select, update


@pytest.mark.parametrize(
    "phase",
    ["prepared", "source", "before_commit", "after_commit", "cleanup_before_commit"],
)
def test_pg018_os_death_before_or_after_commit_is_atomic_and_retryable(
    pg_engines, pg_publisher, tmp_path, phase
):
    old = publish(pg_publisher, source("テスト旧公開"))
    before = digest(pg_engines[0])
    raw = source("テスト中断新版", revised_at="2026-11")
    ready = tmp_path / "owned-crash-ready"
    with (tmp_path / "owned-crash.log").open("w", encoding="utf-8") as log:
        child = subprocess.Popen(
            [sys.executable, "-m", "backend.tests.support.postgres_crash_worker"],
            cwd=PROJECT_ROOT,
            env={
                **os.environ,
                "PYTHONUTF8": "1",
                "PG_WORKER_SCHEMA": pg_engines[2],
                "PG_WORKER_SOURCE": base64.b64encode(raw).decode("ascii"),
                "PG_CRASH_READY": str(ready),
                "PG_CRASH_PHASE": phase,
            },
            stdin=subprocess.PIPE,
            stdout=log,
            stderr=log,
        )
        try:
            deadline = time.monotonic() + 20
            while not ready.exists():
                assert child.poll() is None, "Owned crash child exited before barrier"
                assert time.monotonic() < deadline, "Owned crash barrier timed out"
                time.sleep(0.02)
            assert ready.read_text(encoding="utf-8") == phase
            child.kill()
            child.wait(timeout=10)
            committed = phase in {"after_commit", "cleanup_before_commit"}
            if not committed:
                assert digest(pg_engines[0]) == before
            else:
                with pg_engines[0].connect() as connection:
                    assert connection.execute(
                        select(schema.receipts.c.sequence).order_by(
                            schema.receipts.c.sequence
                        )
                    ).scalars().all() == [1, 2]
                verify_postgres_readiness(pg_engines[1])
            result = publish(pg_publisher, raw)
            assert result.registration_sequence == 2
            assert result.reused is committed
            assert result.generation_id != old.generation_id
            verify_postgres_readiness(pg_engines[1])
            assert pg_engines[1].pool.checkedout() == 0
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=10)
            if child.stdin is not None:
                child.stdin.close()


def test_tc099_two_actual_main_processes_refresh_candidates_and_restart_get(
    pg_engines, pg_publisher, tmp_path
):
    first = publish(pg_publisher, source("旧本文"))
    with (
        main_server(pg_engines[2], tmp_path) as (one, p1, _),
        main_server(pg_engines[2], tmp_path) as (two, p2, _),
    ):
        assert p1.pid != p2.pid
        assert one.get("/api/medicines").json()["generation_id"] == first.generation_id
        assert two.get("/api/medicines").json()["generation_id"] == first.generation_id
        replacement = source("新版本文", revised_at="2026-11").replace(
            "製品A".encode(), "新版製品".encode()
        )
        response = one.post(
            "/api/attachment-imports",
            files={"file": ("replacement.xml", replacement, "application/xml")},
        )
        assert response.status_code == 201, response.text
        final = response.json()
        for client in (one, two):
            assert (
                client.get("/health").json()["generation_id"] == final["generation_id"]
            )
            grouped = client.get("/api/medicines").json()
            assert grouped["generation_id"] == final["generation_id"]
            assert grouped["items"][0]["brand_names"] == ["新版製品"]
            assert (
                client.get("/api/medicines/autocomplete").json()["items"][0]["n"]
                == "新版製品"
            )
    with main_server(pg_engines[2], tmp_path) as (client, _, _):
        current = client.get(
            f"/api/attachment-imports/{final['document_id']}/{final['source_sha256']}"
        )
        assert current.status_code == 200
        assert current.json()["generation_id"] == final["generation_id"]
        assert (
            client.get(
                f"/api/attachment-imports/{first.document_id}/{first.source_sha256}"
            ).status_code
            == 410
        )


@pytest.mark.parametrize("component", ["table", "reference", "metadata", "figure"])
def test_tc116_independent_db_payload_damage_refuses_actual_main(
    pg_engines, pg_publisher, tmp_path, component
):
    raw = (
        mixed_source()
        .replace(b"<Warnings>", b'<Warnings id="warnings-target">')
        .replace(
            b"</Warnings>",
            b'<Detail><Lang><HeaderRef ref="warnings-target"/></Lang></Detail></Warnings>',
        )
    )
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
        if component == "figure":
            connection.execute(update(schema.assets).values(content=b"BAD89a"))
        elif component == "metadata":
            catalogue = connection.execute(
                select(schema.versions.c.catalogue)
            ).scalar_one()
            catalogue["source"]["pmda_url"] = (
                "https://example.test/independently-damaged"
            )
            connection.execute(update(schema.versions).values(catalogue=catalogue))
        else:
            row = connection.execute(select(schema.units)).mappings().first()
            assert row is not None
            values = connection.execute(
                select(schema.units.c.unit_id, schema.units.c.payload_json)
            ).all()

            def mutate(node):
                if isinstance(node, dict):
                    if (
                        component == "table"
                        and node.get("text") == "A値"
                        and "colspan" in node
                    ):
                        node["text"] = "独立表cell改変"
                        return True
                    if (
                        component == "reference"
                        and node.get("target_xml_id") == "warnings-target"
                    ):
                        node["target_xml_id"] = "independent-changed-target"
                        return True
                    return any(mutate(value) for value in node.values())
                if isinstance(node, list):
                    return any(mutate(value) for value in node)
                return False

            changed = False
            for identity, serialized in values:
                payload = json.loads(serialized)
                if mutate(payload):
                    connection.execute(
                        update(schema.units)
                        .where(schema.units.c.unit_id == identity)
                        .values(payload_json=json.dumps(payload, ensure_ascii=False))
                    )
                    changed = True
                    break
            assert changed, "Independent table/reference field was absent from fixture"
        assert connection.execute(select(schema.versions.c.source)).scalar_one() == raw
    with main_server(pg_engines[2], tmp_path) as (_, process, log):
        assert process.poll() is not None
        assert process.returncode != 0
        expected = (
            "stored_structure_invalid"
            if component == "metadata"
            else "payload_integrity_invalid"
        )
        assert expected in log.read_text(encoding="utf-8")
