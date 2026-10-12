"""Actual legacy-copy migration and explicit initialization for browser recovery."""

import argparse
import json
import shutil
from pathlib import Path

from backend.project_paths import PROJECT_ROOT
from backend.tests.startup_recovery_fixture import create_legacy_copy
from backend.tests.test_alembic_migrations import _migrate_database
from backend.tests.test_registration_initialization import command


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--old-index", type=Path)
    parser.add_argument("--initialize", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    if not args.initialize:
        if args.old_index is None:
            raise ValueError("explicit legacy index required")
        create_legacy_copy(root, args.old_index)
        shutil.copytree(PROJECT_ROOT / "data/pmda/originals", root / "originals")
        return
    index = root / "index.sqlite3"
    _migrate_database(index, root / "structured")
    completed = command(
        root,
        "backend.infrastructure.cli.initialize_registrations",
        "--originals-dir",
        root / "originals",
        "--structured-dir",
        root / "structured",
        "--index-path",
        index,
        "--import-dir",
        root / "imports",
    )
    print(completed.stdout, flush=True)
    if completed.returncode:
        raise RuntimeError(completed.stderr)
    payload = json.loads(completed.stdout)
    assert (
        payload["registered"],
        payload["documents"],
        payload["units"],
        payload["medicines"],
    ) == (7, 7, 267, 15)


if __name__ == "__main__":
    main()
