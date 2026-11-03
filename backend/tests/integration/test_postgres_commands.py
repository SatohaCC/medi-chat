"""PG-042/043: explicitly selected DB commands, no startup side effects."""

import os
import subprocess
import sys

import pytest
from alembic import command
from alembic.config import Config
from backend.infrastructure.persistence.runtime.postgres_readiness import (
    verify_postgres_readiness,
)
from backend.infrastructure.persistence.schemas import (
    package_insert_tables as postgres_schema,
)
from backend.tests.integration.test_postgres_registration import (
    pg_publisher as pg_publisher,
)
from backend.tests.integration.test_postgres_registration import publish
from backend.tests.support.paths import PROJECT_ROOT
from backend.tests.support.postgres_fixtures import pg_engines as pg_engines
from backend.tests.support.registration_oracles import source
from sqlalchemy import insert, select, text, update


def test_pg042_explicit_migration_command_is_idempotent(pg_engines):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "backend.infrastructure.cli.manage_postgres",
            "--database-env",
            "TEST_DATABASE_URL",
            "--schema",
            pg_engines[2],
            "migrate",
        ],
        cwd=PROJECT_ROOT,
        env={**os.environ, "PYTHONUTF8": "1"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert '"migration": "complete"' in result.stdout


def test_tc112_initial_conflict_lists_public_ids_without_database_or_source_change(
    pg_engines, tmp_path
):
    from backend.tests.support.postgres_observations import digest

    originals = tmp_path / "originals"
    originals.mkdir()
    values = {name: source("衝突", doc=name) for name in ("O", "Q")}
    for name, value in values.items():
        (originals / f"{name}.xml").write_bytes(value)
    before = digest(pg_engines[0])
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "backend.infrastructure.cli.manage_postgres",
            "--database-env",
            "TEST_RUNTIME_DATABASE_URL",
            "--schema",
            pg_engines[2],
            "initialize",
            "--originals-dir",
            str(originals),
        ],
        cwd=PROJECT_ROOT,
        env={**os.environ, "PYTHONUTF8": "1"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=20,
    )
    assert completed.returncode != 0
    assert "same_revision_conflict" in completed.stderr
    assert all(
        value in completed.stderr
        for value in ("111111111111", "000001_O:", "000001_Q:")
    )
    assert digest(pg_engines[0]) == before
    assert {path.stem: path.read_bytes() for path in originals.iterdir()} == values


def test_pg043_pure_offline_conversion_ignores_database_settings(tmp_path):
    original = tmp_path / "テスト.xml"
    original.write_bytes(source("テストオフライン"))
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "backend.infrastructure.cli.structure_pmda_xml",
            str(original),
            "--output-dir",
            str(tmp_path / "output"),
        ],
        cwd=PROJECT_ROOT,
        env={
            **os.environ,
            "PYTHONUTF8": "1",
            "MEDI_CHAT_DATABASE_URL": "deliberately-invalid",
        },
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "output" / "document.json").is_file()
    assert (tmp_path / "output" / "search_units.jsonl").is_file()


def test_pg044_forward_migration_renames_legacy_attachment_tables_and_preserves_rows(
    pg_engines, pg_publisher
):
    from datetime import UTC, datetime
    from hashlib import sha256

    raw = source("migration rename preservation")
    publish(pg_publisher, raw)
    upload_id = "migration-rename-upload"
    upload_bytes = b"migration upload bytes"
    with pg_engines[0].begin() as connection:
        connection.execute(
            insert(postgres_schema.uploads).values(
                upload_id=upload_id,
                filename="migration.xml",
                byte_size=len(upload_bytes),
                source_sha256=sha256(upload_bytes).hexdigest(),
                expires_at=datetime(2026, 11, 4, tzinfo=UTC),
                document_id=None,
            )
        )
        connection.execute(
            insert(postgres_schema.upload_parts).values(
                upload_id=upload_id,
                part_index=0,
                content=upload_bytes,
            )
        )
        stored_version = connection.execute(
            select(
                postgres_schema.versions.c.version_id,
                postgres_schema.versions.c.source,
                postgres_schema.versions.c.structure,
                postgres_schema.versions.c.catalogue,
            )
        ).one()
        assert stored_version.structure["transformer_version"] == (
            "package-insert-domain.v1"
        )

    config = Config(str(PROJECT_ROOT / "backend" / "postgres-alembic.ini"))
    with pg_engines[0].begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "pg_20261024_05")

    with pg_engines[0].connect() as connection:
        legacy_tables = set(
            connection.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema=current_schema()"
                )
            ).scalars()
        )
        assert {
            "attachment_versions",
            "attachment_assets",
            "attachment_uploads",
            "attachment_upload_parts",
        } <= legacy_tables
        assert connection.execute(
            text("SELECT upload_id, part_index, content FROM attachment_upload_parts")
        ).one() == (upload_id, 0, upload_bytes)
        assert connection.execute(
            text("SELECT version_id, source FROM attachment_versions")
        ).one() == (stored_version.version_id, stored_version.source)
        assert connection.execute(
            text(
                "SELECT structure->>'transformer_version', "
                "payload_fingerprint = md5(structure::text || catalogue::text) "
                "FROM attachment_versions"
            )
        ).one() == ("attachment-domain.v1", True)
        legacy_version = connection.execute(
            text("SELECT structure, catalogue FROM attachment_versions")
        ).one()
        assert legacy_version.structure == {
            **stored_version.structure,
            "transformer_version": "attachment-domain.v1",
        }
        assert legacy_version.catalogue == stored_version.catalogue

    with pg_engines[0].begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")

    with pg_engines[0].connect() as connection:
        migrated_tables = set(
            connection.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema=current_schema()"
                )
            ).scalars()
        )
        assert {
            "package_insert_versions",
            "package_insert_assets",
            "package_insert_uploads",
            "package_insert_upload_parts",
        } <= migrated_tables
        assert (
            not {
                "attachment_versions",
                "attachment_assets",
                "attachment_uploads",
                "attachment_upload_parts",
            }
            & migrated_tables
        )
        assert (
            connection.execute(
                select(
                    postgres_schema.versions.c.version_id,
                    postgres_schema.versions.c.source,
                    postgres_schema.versions.c.structure,
                    postgres_schema.versions.c.catalogue,
                )
            ).one()
            == stored_version
        )
        assert connection.execute(
            select(
                postgres_schema.upload_parts.c.upload_id,
                postgres_schema.upload_parts.c.part_index,
                postgres_schema.upload_parts.c.content,
            )
        ).one() == (upload_id, 0, upload_bytes)
        assert connection.execute(
            text(
                "SELECT structure->>'transformer_version', "
                "payload_fingerprint = md5(structure::text || catalogue::text) "
                "FROM package_insert_versions"
            )
        ).one() == ("package-insert-domain.v1", True)

    verify_postgres_readiness(pg_engines[1])


def test_pg042_structure_register_uses_explicit_postgres_target(pg_engines, tmp_path):
    raw = source("テストCLI登録")
    original = tmp_path / "テスト.xml"
    original.write_bytes(raw)
    command = [
        sys.executable,
        "-m",
        "backend.infrastructure.cli.structure_pmda_xml",
        str(original),
        "--register",
        "--database-env",
        "TEST_RUNTIME_DATABASE_URL",
        "--schema",
        pg_engines[2],
    ]
    for reused in (False, True):
        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            env={**os.environ, "PYTHONUTF8": "1"},
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=20,
        )
        assert result.returncode == 0, result.stderr
        import json

        assert json.loads(result.stdout)["registered"][0]["reused"] is reused
    with pg_engines[0].connect() as connection:
        assert (
            bytes(
                connection.execute(
                    select(postgres_schema.versions.c.source)
                ).scalar_one()
            )
            == raw
        )
    assert not list(tmp_path.rglob("document.json"))


def test_pg043_rebuild_from_complete_db_structure_preserves_publication_and_bytes(
    pg_engines, pg_publisher
):
    publish(pg_publisher, source("テスト旧A/B", ("111111111111", "222222222222")))
    publish(pg_publisher, source("テスト新A", revised_at="2026-11"))

    def records(table):
        with pg_engines[0].connect() as connection:
            return sorted(
                [dict(row) for row in connection.execute(select(table)).mappings()],
                key=repr,
            )

    expected_units = records(postgres_schema.units)
    expected_products = records(postgres_schema.unit_products)
    expected_receipts = records(postgres_schema.receipts)
    expected_versions = records(postgres_schema.versions)
    expected_state = records(postgres_schema.state)
    with pg_engines[0].begin() as connection:
        connection.execute(update(postgres_schema.units).values(query_text="破損"))
        connection.execute(postgres_schema.unit_products.delete())
    with pytest.raises(RuntimeError, match="payload_integrity_invalid"):
        verify_postgres_readiness(pg_engines[1])
    script = "from backend.infrastructure.pmda_xml.pmda_xml_decoder import PmdaXmlDecoder; PmdaXmlDecoder.decode=lambda *a, **k: (_ for _ in ()).throw(AssertionError('DB rebuild must restore the complete structure')); from backend.infrastructure.cli.manage_postgres import main; raise SystemExit(main())"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            "--database-env",
            "TEST_RUNTIME_DATABASE_URL",
            "--schema",
            pg_engines[2],
            "rebuild",
            "--confirm-schema",
            pg_engines[2],
        ],
        cwd=PROJECT_ROOT,
        env={**os.environ, "PYTHONUTF8": "1"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert records(postgres_schema.units) == expected_units
    assert records(postgres_schema.unit_products) == expected_products
    assert records(postgres_schema.receipts) == expected_receipts
    assert records(postgres_schema.versions) == expected_versions
    assert records(postgres_schema.state) == expected_state
    verify_postgres_readiness(pg_engines[1])


@pytest.mark.parametrize("condition", ["confirmation", "source", "structure"])
def test_pg043_rebuild_refuses_unconfirmed_or_untrusted_payload_without_writes(
    pg_engines, pg_publisher, condition
):
    raw = source("テスト再構築拒否")
    publish(pg_publisher, raw)
    with pg_engines[0].begin() as connection:
        if condition == "source":
            connection.execute(
                update(postgres_schema.versions).values(source=b"x" * len(raw))
            )
        elif condition == "structure":
            connection.execute(
                update(postgres_schema.versions).values(
                    structure={"schema_version": 999}
                )
            )
    from backend.tests.support.postgres_observations import digest

    before = digest(pg_engines[0])
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "backend.infrastructure.cli.manage_postgres",
            "--database-env",
            "TEST_RUNTIME_DATABASE_URL",
            "--schema",
            pg_engines[2],
            "rebuild",
            "--confirm-schema",
            "public" if condition == "confirmation" else pg_engines[2],
        ],
        cwd=PROJECT_ROOT,
        env={**os.environ, "PYTHONUTF8": "1"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=20,
    )
    assert result.returncode != 0
    assert "PostgreSQL operation refused" in result.stderr
    assert digest(pg_engines[0]) == before
