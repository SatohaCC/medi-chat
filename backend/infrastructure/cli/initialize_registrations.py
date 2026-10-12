"""Backup後の明示初期登録。既存原物を書き換えない。"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from ...application.attachment_import.import_errors import AttachmentImportError
from ..composition.index_verifier import verify_schema_readiness
from ..package_insert_definitions.loader import get_package_insert_definitions
from ..persistence.registration_publisher import (
    RegistrationInput,
    SqliteRegistrationPublisher,
)
from ..pmda_xml.decoder import PmdaXmlDecoder
from ..pmda_xml.safe_parser import parse_source
from ..sources.attachment_import_store import FileAttachmentImportStore


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("originals-dir", "structured-dir", "index-path", "import-dir"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    xml_settings = get_package_insert_definitions().xml_settings
    originals = args.originals_dir.resolve()
    structured = args.structured_dir.resolve()
    index = args.index_path.resolve()
    imports = args.import_dir.resolve()
    try:
        verify_schema_readiness(index)
        with sqlite3.connect(index.as_uri() + "?mode=ro", uri=True) as connection:
            if connection.execute("SELECT COUNT(*) FROM registration_state").fetchone()[
                0
            ]:
                raise RuntimeError(
                    "Already initialized: use the common registration publisher, never rescan inactive originals"
                )
        inputs = []
        for source_path in sorted(originals.rglob("*.xml")):
            source = source_path.read_bytes()
            root, _ = parse_source(source)
            assets = {}
            paths = [source_path]
            for element in root.iter():
                name = element.attrib.get("gfname")
                if not name:
                    continue
                path = source_path.parent / name
                if (
                    ".." in Path(name).parts
                    or Path(name).is_absolute()
                    or path.is_symlink()
                    or not path.resolve().is_relative_to(originals)
                ):
                    raise ValueError("Unsafe initial figure inventory")
                if path.is_file():
                    assets[name] = path.read_bytes()
                    paths.append(path)
            decoded = PmdaXmlDecoder(
                xml_settings=xml_settings,
                assets=assets,
                strict_assets=True,
                source_filename=source_path.as_posix(),
            ).decode(source)
            document_dir = structured / decoded.document.document_id.value
            for name in (
                "document.json",
                "search_units.jsonl",
                "validation.json",
                "source_metadata.json",
                "result.json",
            ):
                path = document_dir / name
                if path.is_file():
                    paths.append(path)
            legacy_document = document_dir / "document.json"
            payload = (
                json.loads(legacy_document.read_bytes())
                if legacy_document.is_file()
                else None
            )
            inputs.append(
                RegistrationInput(
                    decoded, source, tuple(dict.fromkeys(paths)), source_path, payload
                )
            )
        if not inputs:
            raise ValueError("No original XML files to initialize")
        publisher = SqliteRegistrationPublisher(
            index,
            FileAttachmentImportStore(imports),
            xml_settings=xml_settings,
            allowed_roots=(originals, structured),
        )
        results = publisher.publish_inputs(tuple(inputs), initial=True)
        with sqlite3.connect(index.as_uri() + "?mode=ro", uri=True) as connection:
            counts = {
                table: connection.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
                for table in ("documents", "units", "medicines")
            }
        print(
            json.dumps(
                {
                    "registered": len(results),
                    "generation_id": results[0].generation_id,
                    **counts,
                },
                ensure_ascii=False,
            )
        )
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
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1
    except (RuntimeError, ValueError, OSError, sqlite3.DatabaseError) as error:
        print(f"Initial registration refused: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
