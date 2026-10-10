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
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from .pmda_xml.transform import transform
from .pmda_xml.xml_nodes import relative_path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


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
    args = arg_parser.parse_args()

    if args.source_dir is not None:
        source_dir = args.source_dir
        if not source_dir.is_dir():
            arg_parser.error(f"Source directory does not exist: {source_dir}")
        xml_files = sorted(source_dir.rglob("*.xml"))
        if not xml_files:
            print(f"No XML files found in {source_dir}", file=sys.stderr)
            return 1
        base_output_dir = args.output_dir or (PROJECT_ROOT / "structured")
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
                res = transform(xml_file, target_dir)
                results.append(
                    {
                        "xml": str(xml_file),
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
            PROJECT_ROOT / "structured" / f"{match.group(1)}_{match.group(2)}"
        )
    try:
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


if __name__ == "__main__":
    raise SystemExit(main())
