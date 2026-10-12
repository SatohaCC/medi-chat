"""Actual main/HTTP server with a test-only publisher phase barrier."""

import argparse
import time
from pathlib import Path

import uvicorn
from backend import main as application_main
from backend.infrastructure.persistence.registration_publisher import (
    SqliteRegistrationPublisher,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    for name in ("index", "imports", "structured", "ready"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()

    def stop(point: str) -> None:
        if point == args.phase:
            args.ready.write_text(point, encoding="ascii")
            while True:
                time.sleep(0.05)

    class ControlledPublisher(SqliteRegistrationPublisher):
        def __init__(self, *positional, **keywords):
            super().__init__(*positional, **keywords, fault=stop)

    application_main.SqliteRegistrationPublisher = ControlledPublisher
    uvicorn.run(
        application_main.create_app(
            args.structured, args.index, import_directory=args.imports
        ),
        host="127.0.0.1",
        port=args.port,
    )


if __name__ == "__main__":
    main()
