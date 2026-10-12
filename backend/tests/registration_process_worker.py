"""実OS publisher試験のbarrier harness。外部SDK/HTTPを使用しない。"""

import argparse
import asyncio
import contextlib
import io
import json
import os
import sys
import time
from pathlib import Path

from backend.infrastructure.persistence.registration_publisher import (
    SqliteRegistrationPublisher,
)
from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder
from backend.infrastructure.sources.attachment_import_store import (
    FileAttachmentImportStore,
)


def main():
    parser = argparse.ArgumentParser()
    for name in ("source", "index", "imports", "parsed", "release"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument(
        "--mode", choices=("publisher", "cli", "api"), default="publisher"
    )
    args = parser.parse_args()
    source = args.source.read_bytes()

    class ControlledDecoder(PmdaXmlDecoder):
        def decode(self, source, *, original_filename=None):
            decoded = super().decode(source, original_filename=original_filename)
            marker = args.parsed.with_suffix(".writing")
            marker.write_text(str(os.getpid()), encoding="ascii")
            marker.replace(args.parsed)
            deadline = time.monotonic() + 45
            while not args.release.exists():
                if time.monotonic() > deadline:
                    raise TimeoutError("explicit publish barrier not released")
                time.sleep(0.01)
            return decoded

    if args.mode == "cli":
        from backend.infrastructure.cli import structure_pmda_xml
        from backend.infrastructure.pmda_xml import decoder

        decoder.PmdaXmlDecoder = ControlledDecoder
        sys.argv = [
            "structure_pmda_xml",
            str(args.source),
            "--register",
            "--index-path",
            str(args.index),
            "--import-dir",
            str(args.imports),
        ]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = structure_pmda_xml.main()
        assert code == 0
        print(json.loads(output.getvalue())["registered"][0]["registration_sequence"])
        return
    if args.mode == "api":
        import httpx
        from backend.application.attachment_import.import_document import (
            AttachmentImportService,
        )
        from backend.infrastructure.pmda_xml.artifact_mapping import PmdaArtifactEncoder
        from backend.presentation.attachment_import_routes import router
        from fastapi import FastAPI

        async def run():
            store = FileAttachmentImportStore(args.imports)
            service = AttachmentImportService(
                decoder=ControlledDecoder(),
                encoder=PmdaArtifactEncoder(),
                store=store,
                publisher=SqliteRegistrationPublisher(args.index, store),
            )
            app = FastAPI()
            app.include_router(router)
            app.state.attachment_import_service = service
            try:
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.post(
                        "/api/attachment-imports",
                        files={"file": ("source.xml", source, "application/xml")},
                    )
                    assert response.status_code == 201, response.text
                    return response.json()["registration_sequence"]
            finally:
                await service.aclose()

        print(asyncio.run(run()))
        return
    decoded = ControlledDecoder().decode(source)
    result = SqliteRegistrationPublisher(
        args.index, FileAttachmentImportStore(args.imports)
    ).publish(decoded, source)
    print(result.registration_sequence)


if __name__ == "__main__":
    main()
