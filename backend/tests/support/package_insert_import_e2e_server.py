"""Dedicated real HTTP server using one explicitly owned browser PostgreSQL schema."""

import argparse
import os
from pathlib import Path

import uvicorn
from backend.tests.support.authentication import (
    SignedTestActor,
    authentication_environment,
)
from backend.tests.support.postgres_browser_fixture import prepare, selected_url


def prepare_root(root: Path) -> str:
    return prepare(root)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    schema = prepare_root(args.root)
    os.environ["MEDI_CHAT_DATABASE_URL"] = selected_url()
    os.environ.update(authentication_environment())
    os.environ.pop("AUTH_PRIVATE_KEY_FILE", None)
    from backend.main import create_app

    app = create_app(database_url=selected_url(), _database_schema=schema)
    app.add_middleware(SignedTestActor)
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=args.port,
    )


if __name__ == "__main__":
    main()
