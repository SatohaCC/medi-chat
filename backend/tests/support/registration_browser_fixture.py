"""Fresh current-format registration data for browser tests."""

import argparse
import shutil
from pathlib import Path

from backend.project_paths import PROJECT_ROOT
from backend.tests.infrastructure.persistence.test_alembic_migrations import (
    _migrate_database,
)
from backend.tests.integration.test_registration_initialization import command


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    originals = root / "originals"
    structured = root / "structured"
    structured.mkdir(parents=True, exist_ok=True)
    shutil.copytree(PROJECT_ROOT / "data/pmda/originals", originals)
    index = root / "index.sqlite3"
    _migrate_database(index, structured)
    completed = command(
        root,
        "backend.infrastructure.cli.initialize_registrations",
        "--originals-dir",
        originals,
        "--structured-dir",
        structured,
        "--index-path",
        index,
        "--import-dir",
        root / "imports",
    )
    print(completed.stdout, flush=True)
    if completed.returncode:
        raise RuntimeError(completed.stderr)


if __name__ == "__main__":
    main()
