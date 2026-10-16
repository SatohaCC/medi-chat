"""Turn a PMDA prescription-drug package-insert XML into reviewable JSON.

The original XML remains the source of truth.  document.json retains the XML
hierarchy (including mixed text, processing instructions, attributes, and table
spans); search_units.jsonl is a derived, version-bound retrieval index.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import sqlite3
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from ...project_paths import PROJECT_ROOT, resolve_project_path
from ..package_insert_definitions.loader import get_package_insert_definitions
from ..pmda_xml.transform import transform
from ..pmda_xml.xml_nodes import relative_path


def main() -> int:
    arg_parser = argparse.ArgumentParser(description=__doc__)
    arg_parser.add_argument(
        "xml",
        nargs="?",
        type=Path,
        default=None,
        help="Downloaded PMDA PackIns XML (single file mode)",
    )
    arg_parser.add_argument(
        "--source-dir",
        type=Path,
        default=None,
        help="Directory containing PMDA XML files to process in batch",
    )
    arg_parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: structured/<company>_<insert-no> or structured/ for batch)",
    )
    arg_parser.add_argument(
        "--register",
        action="store_true",
        help="Register through the common publisher; not an offline output conversion",
    )
    arg_parser.add_argument("--index-path", type=Path, default=None)
    arg_parser.add_argument("--import-dir", type=Path, default=None)
    args = arg_parser.parse_args()
    if args.register:
        return _register(args)
    for name in ("xml", "source_dir", "output_dir"):
        path = getattr(args, name)
        if path is not None:
            setattr(args, name, resolve_project_path(path))

    if args.source_dir is not None:
        source_dir = args.source_dir
        if not source_dir.is_dir():
            arg_parser.error(f"Source directory does not exist: {source_dir}")
        xml_files = sorted(source_dir.rglob("*.xml"))
        if not xml_files:
            print(f"No XML files found in {source_dir}", file=sys.stderr)
            return 1
        base_output_dir = args.output_dir or (PROJECT_ROOT / "data/pmda/structured")
        base_output_dir.mkdir(parents=True, exist_ok=True)
        results = []
        for xml_file in xml_files:
            match = re.fullmatch(r"(\d+)_(.+)\.xml", xml_file.name)
            target_dir = (
                base_output_dir / f"{match.group(1)}_{match.group(2)}"
                if match
                else base_output_dir / xml_file.stem
            )
            try:
                _guard_managed_output(target_dir, args.index_path, args.import_dir)
                res = transform(xml_file, target_dir)
                results.append(
                    {
                        "xml": relative_path(xml_file),
                        "output_dir": relative_path(target_dir),
                        "status": res.get("status"),
                    }
                )
            except Exception as exc:
                print(f"ERROR processing {xml_file}: {exc}", file=sys.stderr)
                return 1
        manifest = {
            "schema_version": "1.0",
            "document_count": len(results),
            "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
            "sha256": hashlib.sha256(
                "".join(sorted(f"{r['xml']}:{r['status']}" for r in results)).encode(
                    "utf-8"
                )
            ).hexdigest(),
        }
        (base_output_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(
            json.dumps(
                {"processed_count": len(results), "results": results},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if args.xml is None:
        arg_parser.error("Either positional 'xml' or '--source-dir' must be provided.")

    if args.output_dir is None:
        match = re.fullmatch(r"(\d+)_(.+)\.xml", args.xml.name)
        if not match:
            arg_parser.error("Use --output-dir for XML files without a PMDA filename")
        args.output_dir = (
            PROJECT_ROOT / "data/pmda/structured" / f"{match.group(1)}_{match.group(2)}"
        )
    try:
        _guard_managed_output(args.output_dir, args.index_path, args.import_dir)
        result = transform(args.xml, args.output_dir)
    except (ET.ParseError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {"output_dir": relative_path(args.output_dir), **result},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _guard_managed_output(
    target: Path, index_path: Path | None, import_dir: Path | None
) -> None:
    from ...config.database_settings import resolve_database_settings
    from ...config.import_settings import resolve_import_directory

    resolved = resolve_project_path(target)
    root = (
        resolve_project_path(import_dir) if import_dir else resolve_import_directory()
    )
    if resolved.is_relative_to(root):
        raise ValueError("Offline conversion cannot overwrite managed import artifacts")
    index = resolve_database_settings(index_path=index_path).index_path
    if not index.is_file():
        return
    with sqlite3.connect(index.as_uri() + "?mode=ro", uri=True) as connection:
        if not connection.execute(
            "SELECT name FROM sqlite_master WHERE name='registration_owned_files'"
        ).fetchone():
            return
        owned = [
            Path(row[0])
            for row in connection.execute(
                "SELECT file_id FROM registration_owned_files"
            )
        ]
    for name in (
        "document.json",
        "search_units.jsonl",
        "validation.json",
        "manifest.json",
    ):
        if resolved / name in owned:
            raise ValueError(
                "Offline conversion cannot overwrite managed registration artifacts"
            )


def _register(args: argparse.Namespace) -> int:
    from ...application.attachment_import.import_errors import AttachmentImportError
    from ...config.database_settings import resolve_database_settings
    from ...config.import_settings import resolve_import_directory
    from ..composition.index_verifier import verify_schema_readiness
    from ..persistence.attachment_import_store import FileAttachmentImportStore
    from ..persistence.registration_publisher import SqliteRegistrationPublisher
    from ..pmda_xml.decoder import PmdaXmlDecoder
    from ..pmda_xml.safe_parser import parse_source

    if args.output_dir is not None:
        print(
            "ERROR: --output-dir is an offline conversion destination; omit it in --register mode",
            file=sys.stderr,
        )
        return 1
    settings = resolve_database_settings(index_path=args.index_path)
    try:
        verify_schema_readiness(settings.index_path)
        with sqlite3.connect(
            settings.index_path.as_uri() + "?mode=ro", uri=True
        ) as connection:
            if not connection.execute(
                "SELECT generation_id FROM registration_state"
            ).fetchone():
                raise ValueError(
                    "initial_registration_required: run initialize_registrations first"
                )
        paths = (
            sorted(resolve_project_path(args.source_dir).rglob("*.xml"))
            if args.source_dir is not None
            else [resolve_project_path(args.xml)]
            if args.xml is not None
            else []
        )
        if not paths:
            raise ValueError("No original XML files selected")
        xml_settings = get_package_insert_definitions().xml_settings
        publisher = SqliteRegistrationPublisher(
            settings.index_path,
            FileAttachmentImportStore(
                resolve_project_path(args.import_dir)
                if args.import_dir is not None
                else resolve_import_directory()
            ),
            xml_settings=xml_settings,
            allowed_roots=(
                settings.structured_dir,
                settings.structured_dir.parent / "originals",
            ),
        )
        results = []
        for path in paths:
            source = path.read_bytes()
            root, _ = parse_source(source)
            assets = {}
            for element in root.iter():
                filename = element.attrib.get("gfname")
                if not filename:
                    continue
                figure = path.parent / filename
                if (
                    ".." in Path(filename).parts
                    or Path(filename).is_absolute()
                    or figure.is_symlink()
                    or not figure.resolve().is_relative_to(path.parent)
                ):
                    raise ValueError("Unsafe strict figure reference")
                if figure.is_file():
                    assets[filename] = figure.read_bytes()
            decoded = PmdaXmlDecoder(
                xml_settings=xml_settings,
                assets=assets,
                strict_assets=True,
                source_filename=path.as_posix(),
            ).decode(source)
            result = publisher.publish(decoded, source)
            results.append(
                {
                    "document_id": result.document_id,
                    "status": result.status,
                    "reused": result.reused,
                    "registration_sequence": result.registration_sequence,
                    "generation_id": result.generation_id,
                }
            )
        print(json.dumps({"registered": results}, ensure_ascii=False))
        return 0
    except AttachmentImportError as error:
        print(f"ERROR: {error.phase}/{error.code}: {error.message}", file=sys.stderr)
        return 1
    except (RuntimeError, ValueError, OSError, sqlite3.DatabaseError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
