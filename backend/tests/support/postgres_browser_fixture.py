"""Explicitly owned per-browser-run PostgreSQL schemas; no developer DB writes."""

import argparse
import hashlib
import json
import os
import uuid
from pathlib import Path

from alembic import command
from alembic.config import Config
from backend.infrastructure.cli.manage_postgres import load_inputs
from backend.infrastructure.persistence.registration.postgres_registration_publisher import (
    PostgresRegistrationPublisher,
)
from backend.infrastructure.persistence.runtime.postgres_engine import (
    create_postgres_engine,
)
from backend.infrastructure.persistence.runtime.postgres_readiness import (
    verify_postgres_readiness,
)
from backend.infrastructure.pmda_xml.pmda_artifact_encoder import PmdaArtifactEncoder
from backend.infrastructure.pmda_xml.pmda_xml_decoder import PmdaXmlDecoder
from backend.project_paths import BACKEND_DIR, PROJECT_ROOT
from backend.tests.support.attachment_import_fixtures import xml_source
from backend.tests.support.postgres_fixtures import validate_test_database_url
from sqlalchemy import inspect, text


def fixture_schema(root: Path) -> str:
    marker = json.loads((root / "postgres-fixture.json").read_text(encoding="utf-8"))
    schema = marker["schema"]
    if (
        marker["purpose"] != "medi-chat-browser"
        or marker["database"] != "medi_chat_test"
        or not isinstance(schema, str)
        or len(schema) != len("medi_chat_test_") + 32
        or not schema.startswith("medi_chat_test_")
        or any(
            value not in "0123456789abcdef"
            for value in schema.removeprefix("medi_chat_test_")
        )
    ):
        raise ValueError("Refusing unowned browser fixture")
    return schema


def selected_url(*, owner: bool = False) -> str:
    value = os.environ.get(
        "TEST_DATABASE_URL" if owner else "TEST_RUNTIME_DATABASE_URL", ""
    )
    validate_test_database_url(value, runtime=not owner)
    return value


def prepare(root: Path, *, full: bool = False) -> str:
    root.mkdir(parents=True, exist_ok=True)
    if (root / "postgres-fixture.json").exists():
        return fixture_schema(root)
    owner_url = selected_url(owner=True)
    selected_url()
    schema = "medi_chat_test_" + uuid.uuid4().hex
    admin = create_postgres_engine(owner_url)
    try:
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
        engine = None
        try:
            engine = create_postgres_engine(owner_url, schema=schema)
            with engine.begin() as connection:
                config = Config(str(BACKEND_DIR / "postgres-alembic.ini"))
                config.attributes["connection"] = connection
                command.upgrade(config, "head")
            publisher = PostgresRegistrationPublisher(
                engine, encoder=PmdaArtifactEncoder()
            )
            if full:
                publisher.publish_inputs(
                    load_inputs(PROJECT_ROOT / "data/pmda/originals"), initial=True
                )
            else:
                raw = xml_source(
                    "<AdverseEvents><Detail><Lang>テスト初期データ 頭痛に注意してください。</Lang></Detail></AdverseEvents>"
                )
                publisher.publish(PmdaXmlDecoder().decode(raw), raw)
            (root / "postgres-fixture.json").write_text(
                json.dumps(
                    {
                        "purpose": "medi-chat-browser",
                        "database": "medi_chat_test",
                        "schema": schema,
                    }
                ),
                encoding="utf-8",
            )
        except BaseException:
            with admin.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            raise
        finally:
            if engine is not None:
                engine.dispose()
    finally:
        admin.dispose()
    return schema


def cleanup(root: Path) -> None:
    schema = fixture_schema(root)
    engine = create_postgres_engine(selected_url(owner=True))
    try:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        (root / "postgres-fixture.json").unlink()
    finally:
        engine.dispose()


def snapshot(root: Path):
    schema = fixture_schema(root)
    engine = create_postgres_engine(selected_url(), schema=schema)
    try:
        verify_postgres_readiness(engine)
        with engine.connect().execution_options(
            isolation_level="REPEATABLE READ"
        ) as connection:
            connection.execute(text("SET TRANSACTION READ ONLY"))
            inspector = inspect(connection)
            tables = {}
            for name in sorted(inspector.get_table_names(schema=schema)):
                columns = [
                    column["name"]
                    for column in inspector.get_columns(name, schema=schema)
                ]
                rows = connection.execute(text(f'SELECT * FROM "{name}"')).all()
                normalized = [
                    [
                        {
                            "byte_size": len(value),
                            "sha256": hashlib.sha256(value).hexdigest(),
                        }
                        if isinstance(value, bytes)
                        else value
                        for value in row
                    ]
                    for row in rows
                ]
                normalized.sort(key=lambda row: json.dumps(row, sort_keys=True))
                tables[name] = {"columns": columns, "rows": normalized}
            digest = hashlib.sha256(
                json.dumps(tables, ensure_ascii=False, sort_keys=True).encode()
            ).hexdigest()
            return {"integrity": "ok", "logical_sha256": digest, "tables": tables}
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "cleanup", "snapshot"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()
    if args.action == "prepare":
        result = {"schema": prepare(args.root, full=args.full)}
    elif args.action == "cleanup":
        cleanup(args.root)
        result = {"cleanup": "complete"}
    else:
        result = snapshot(args.root)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
