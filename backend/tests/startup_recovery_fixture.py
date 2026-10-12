"""Copy real legacy data without preparing or building a fresh index."""

import argparse
import gzip
import hashlib
import json
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

from backend.infrastructure.cli.index_maintenance import (
    assert_stopped,
    logical_snapshot,
)
from backend.infrastructure.persistence.legacy_content_validator import (
    validate_legacy_content,
)
from backend.project_paths import PROJECT_ROOT


def restore_manifest_v3_fixture(index: Path) -> None:
    """Restore the actual historical manifest backup, never a fresh builder input."""
    fixture = Path(__file__).parent / "fixtures/pre_registration_manifest_v3.sqlite3.gz"
    raw = gzip.decompress(fixture.read_bytes())
    assert len(raw) == 8_511_488
    assert (
        hashlib.sha256(raw).hexdigest()
        == "b079a9696e99e95e3e0ee9e48e4ea9640df91fa09e3817c9ab192ecb6afe6681"
    )
    index.write_bytes(raw)
    snapshot = logical_snapshot(index)
    assert snapshot["integrity"] == "ok"
    assert snapshot["fingerprint"].startswith("manifest:")
    assert (
        snapshot["logical_sha256"]
        == "40399571c204e996f059e8ad683b0002df1a86eeccde3cb5890c8c7a11caf720"
    )
    assert {
        name: snapshot["tables"][name] for name in ("documents", "units", "medicines")
    } == {"documents": 7, "units": 1686, "medicines": 15}
    assert "alembic_version" not in snapshot["tables"]


def create_legacy_copy(root: Path, old_index: Path) -> tuple[Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    source = PROJECT_ROOT / "data/pmda/structured"
    destination = root / "structured"
    ledger = []
    for original in sorted(source.rglob("*")):
        if not original.is_file() or original.suffix not in {".json", ".jsonl"}:
            continue
        copied = destination / original.relative_to(source)
        copied.parent.mkdir(parents=True, exist_ok=True)
        before = original.read_bytes()
        shutil.copy2(original, copied)
        assert copied.read_bytes() == before
        ledger.append(
            {
                "path": original.relative_to(source).as_posix(),
                "sha256": hashlib.sha256(before).hexdigest(),
            }
        )
    index = root / "index.sqlite3"
    old_index = old_index.resolve()
    assert_stopped(old_index)
    with closing(sqlite3.connect(old_index.as_uri() + "?mode=ro", uri=True)) as managed:
        revisions = managed.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchall()
        assert revisions == [("0001_v3_schema",)]
        columns = managed.execute("PRAGMA table_info(alembic_version)").fetchall()
        assert columns == [(0, "version_num", "VARCHAR(32)", 1, None, 1)]
        with closing(sqlite3.connect(":memory:")) as legacy_schema:
            managed.backup(legacy_schema)
            legacy_schema.execute("DROP TABLE alembic_version")
            from backend.infrastructure.persistence.legacy_schema_validator import (
                _validate_schema,
            )

            _validate_schema(legacy_schema)
    validate_legacy_content(old_index)
    snapshot = logical_snapshot(old_index)
    with (
        closing(sqlite3.connect(old_index.as_uri() + "?mode=ro", uri=True)) as original,
        closing(sqlite3.connect(index)) as copied,
    ):
        original.backup(copied)
    assert logical_snapshot(index) == snapshot
    assert_stopped(old_index)
    assert logical_snapshot(old_index) == snapshot
    if not snapshot["fingerprint"].startswith("manifest:"):
        raise RuntimeError(
            "F7 requires the real old manifest index; no fresh substitute"
        )
    (root / "copy-ledger.json").write_text(
        json.dumps(
            {"source_files": ledger, "old_index": str(old_index), "snapshot": snapshot},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return destination, index


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--old-index", type=Path, required=True)
    arguments = parser.parse_args()
    source, index = create_legacy_copy(arguments.root, arguments.old_index)
    print(json.dumps({"structured_dir": str(source), "index_path": str(index)}))
