"""Dedicated real HTTP server with isolated prepared SQLite and import storage."""

import argparse
import os
from pathlib import Path

import uvicorn
from backend.main import create_app
from backend.tests.support.storage_fixtures import (
    build_document_store,
    write_structured_document,
)


def prepare_root(root: Path) -> tuple[Path, Path]:
    index = root / "index.sqlite3"
    structured = root / "structured"
    if not index.exists():
        structured = write_structured_document(root)
        build_document_store(structured, index)
        from backend.tests.support.registration_runtime_fixtures import (
            register_synthetic_prepared_index,
        )

        register_synthetic_prepared_index(structured, index)
    return structured, index


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    args.root.mkdir(parents=True, exist_ok=True)
    structured, index = prepare_root(args.root)
    os.environ["MEDI_CHAT_ORIGINALS_DIR"] = str(args.root / "originals")
    uvicorn.run(
        create_app(structured, index, import_directory=args.root / "imports"),
        host="127.0.0.1",
        port=args.port,
    )


if __name__ == "__main__":
    main()
