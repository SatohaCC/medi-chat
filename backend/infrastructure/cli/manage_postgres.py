"""Explicit PostgreSQL initialization, retained-source export and maintenance."""

import argparse
import hashlib
import json
import mimetypes
import os
import sys
from pathlib import Path, PurePosixPath

from alembic import command
from alembic.config import Config
from sqlalchemy import delete, insert, select, text
from sqlalchemy.exc import SQLAlchemyError

from backend.application.attachment_import.import_errors import AttachmentImportError
from backend.config.runtime_environment import load_runtime_environment
from backend.domain.foundation.json_types import JsonValue
from backend.infrastructure.persistence import postgres_schema as s
from backend.infrastructure.persistence.attachment_document_mapping import (
    document_from_payload,
)
from backend.infrastructure.persistence.postgres_engine import create_postgres_engine
from backend.infrastructure.persistence.postgres_integrity import PROJECTION_FINGERPRINT
from backend.infrastructure.persistence.postgres_projection import projection_records
from backend.infrastructure.persistence.postgres_readiness import (
    verify_postgres_readiness,
)
from backend.infrastructure.persistence.postgres_registration import (
    PostgresRegistrationPublisher,
)
from backend.infrastructure.persistence.postgres_registration_cleanup import (
    PostgresRegistrationCleanup,
)
from backend.infrastructure.persistence.postgres_upload import PostgresUploadStore
from backend.infrastructure.persistence.registration_models import (
    FigureInput,
    PostgresRegistrationInput,
)
from backend.infrastructure.pmda_xml.artifact_mapping import PmdaArtifactEncoder
from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder
from backend.infrastructure.pmda_xml.safe_parser import parse_source
from backend.project_paths import BACKEND_DIR, resolve_project_path


def load_inputs(originals_dir: Path):
    candidate = resolve_project_path(originals_dir)
    if originals_dir.is_symlink():
        raise ValueError("Unsafe original directory")
    inputs = tuple(
        _read_input(path, candidate) for path in sorted(candidate.rglob("*.xml"))
    )
    if not inputs:
        raise ValueError("No original XML files to initialize")
    return inputs


def load_single_input(xml_path: Path):
    if xml_path.is_symlink():
        raise ValueError("Unsafe original XML inventory")
    path = resolve_project_path(xml_path)
    return _read_input(path, path.parent)


def _read_input(path: Path, inventory_root: Path):
    if _unsafe(path, inventory_root):
        raise ValueError("Unsafe original XML inventory")
    raw = path.read_bytes()
    root, _ = parse_source(raw)
    figures = {}
    for element in root.iter():
        name = element.attrib.get("gfname")
        if not name:
            continue
        if not _safe_name(name):
            raise ValueError("Unsafe initial figure inventory")
        asset = path.parent / name
        if _unsafe(asset, inventory_root):
            raise ValueError("Unsafe initial figure inventory")
        if asset.is_file():
            figures[name] = asset.read_bytes()
    decoded = PmdaXmlDecoder(assets=figures, strict_assets=True).decode(
        raw, original_filename=path.name
    )
    return PostgresRegistrationInput(
        decoded,
        raw,
        tuple(
            FigureInput(
                name,
                mimetypes.guess_type(name)[0] or "application/octet-stream",
                content,
            )
            for name, content in sorted(figures.items())
        ),
    )


def _safe_name(name: str) -> bool:
    path = PurePosixPath(name)
    return (
        bool(name)
        and not path.is_absolute()
        and ".." not in path.parts
        and "\\" not in name
        and ":" not in name
    )


def _unsafe(path: Path, root: Path) -> bool:
    return not path.resolve().is_relative_to(root) or any(
        parent.is_symlink()
        for parent in (path, *path.parents)
        if parent.is_relative_to(root)
    )


def export_version(engine, version_id: str, directory: Path):
    with engine.connect().execution_options(
        isolation_level="REPEATABLE READ"
    ) as connection:
        row = (
            connection.execute(
                select(s.versions, s.receipts.c.source_sha256)
                .join(s.receipts, s.receipts.c.version_id == s.versions.c.version_id)
                .where(s.versions.c.version_id == version_id)
            )
            .mappings()
            .first()
        )
        if row is None:
            raise ValueError("Retained source version does not exist")
        assets = list(
            connection.execute(
                select(s.assets).where(s.assets.c.version_id == version_id)
            ).mappings()
        )
    raw = bytes(row["source"])
    if (
        len(raw) != row["byte_size"]
        or hashlib.sha256(raw).hexdigest() != row["source_sha256"]
    ):
        raise ValueError("Stored original integrity mismatch")
    for asset in assets:
        if (
            not _safe_name(asset["logical_name"])
            or hashlib.sha256(asset["content"]).hexdigest() != asset["source_sha256"]
            or len(asset["content"]) != asset["byte_size"]
        ):
            raise ValueError("Stored figure integrity mismatch")
    directory = resolve_project_path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "source.xml").write_bytes(raw)
    for asset in assets:
        path = directory / "figures" / asset["logical_name"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(asset["content"])
    return {
        "filename": row["filename"],
        "byte_size": len(raw),
        "source_sha256": row["source_sha256"],
        "figure_count": len(assets),
    }


def rebuild_projections(engine, *, schema: str, confirm_schema: str):
    if schema != confirm_schema:
        raise ValueError("Rebuild requires exact --confirm-schema target")
    with engine.begin() as connection:
        connection.execute(select(s.state.c.singleton).with_for_update()).scalar_one()
        # Source/structure/catalogue/ownership must be valid. Only explicitly
        # disposable derived rows are allowed to differ before this operation.
        verify_postgres_readiness(engine, projections=False)
        count = 0
        for row in connection.execute(
            select(s.versions.c.version_id, s.versions.c.structure)
        ).yield_per(1):
            units, products = projection_records(document_from_payload(row.structure))
            connection.execute(
                delete(s.units).where(s.units.c.version_id == row.version_id)
            )
            connection.execute(
                delete(s.unit_products).where(
                    s.unit_products.c.version_id == row.version_id
                )
            )
            for unit in units:
                connection.execute(
                    insert(s.units), {"version_id": row.version_id, **unit}
                )
            for product in products:
                connection.execute(
                    insert(s.unit_products), {"version_id": row.version_id, **product}
                )
            connection.execute(
                text(
                    f"UPDATE attachment_versions SET projection_fingerprint={PROJECTION_FINGERPRINT} WHERE version_id=:identity"
                ),
                {"identity": row.version_id},
            )
            count += 1
    return {"rebuild": "complete", "retained_versions": count}


def main() -> int:
    load_runtime_environment()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-env",
        required=True,
        help="Name of environment variable holding the explicit target URL",
    )
    parser.add_argument("--schema", default="public")
    commands = parser.add_subparsers(dest="action", required=True)
    initial = commands.add_parser("initialize")
    initial.add_argument("--originals-dir", type=Path, required=True)
    export = commands.add_parser("export")
    export.add_argument("--version-id", required=True)
    export.add_argument("--output-dir", type=Path, required=True)
    commands.add_parser("maintenance")
    commands.add_parser("migrate")
    rebuild = commands.add_parser("rebuild")
    rebuild.add_argument("--confirm-schema", required=True)
    args = parser.parse_args()
    database_url = os.environ.get(args.database_env)
    if not database_url:
        print("Explicit target database environment variable is unset", file=sys.stderr)
        return 1
    engine = None
    result: dict[str, JsonValue]
    try:
        engine = create_postgres_engine(database_url, schema=args.schema)
        publisher = PostgresRegistrationPublisher(engine, encoder=PmdaArtifactEncoder())
        if args.action == "migrate":
            with engine.begin() as connection:
                config = Config(str(BACKEND_DIR / "postgres-alembic.ini"))
                config.attributes["connection"] = connection
                command.upgrade(config, "head")
            result = {"migration": "complete"}
        elif args.action == "rebuild":
            result = rebuild_projections(
                engine, schema=args.schema, confirm_schema=args.confirm_schema
            )
        elif args.action == "initialize":
            results = publisher.publish_inputs(
                load_inputs(args.originals_dir), initial=True
            )
            result = {
                "registered": len(results),
                "generation_id": results[0].generation_id,
            }
        elif args.action == "export":
            result = export_version(engine, args.version_id, args.output_dir)
        else:
            PostgresRegistrationCleanup(engine).cleanup()
            PostgresUploadStore(engine).cleanup()
            result = {"maintenance": "complete"}
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except AttachmentImportError as error:
        print(
            json.dumps(
                {
                    "code": error.code,
                    "phase": error.phase,
                    "message": error.message,
                    "conflicts": [
                        {"yj_code": code, "version_ids": list(versions)}
                        for code, versions in error.conflicts
                    ],
                }
            ),
            file=sys.stderr,
        )
        return 1
    except OSError, ValueError, RuntimeError, SQLAlchemyError:
        print(
            "PostgreSQL operation refused or failed; verify the explicit target, schema and source inventory",
            file=sys.stderr,
        )
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
