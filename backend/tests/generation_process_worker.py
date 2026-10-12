"""Dedicated OS lease owner controlled by marker files; no SDK calls."""

import argparse
import asyncio
import os
from pathlib import Path

from backend.infrastructure.persistence.generation_runtime import GenerationRuntime
from backend.infrastructure.persistence.read_workers import ReadWorkers
from backend.infrastructure.persistence.registration_publisher import (
    SqliteRegistrationPublisher,
)
from backend.infrastructure.sources.attachment_import_store import (
    FileAttachmentImportStore,
)


async def run(args):
    workers = ReadWorkers()
    runtime = GenerationRuntime(
        SqliteRegistrationPublisher(
            args.index, FileAttachmentImportStore(args.imports)
        ),
        workers=workers,
    )
    try:
        async with runtime.acquire() as snapshot:
            marker = args.ready.with_suffix(".writing")
            marker.write_text(
                str(os.getpid()) + ":" + snapshot.generation_id.value, encoding="ascii"
            )
            marker.replace(args.ready)
            while not args.release.exists():
                await asyncio.sleep(0.01)
    finally:
        await workers.aclose()


def main():
    parser = argparse.ArgumentParser()
    for name in ("index", "imports", "ready", "release"):
        parser.add_argument("--" + name, type=Path, required=True)
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
