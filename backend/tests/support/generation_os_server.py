"""Own one actual main process/port. Never stop an existing server."""

import os
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import httpx
from backend.tests.support.paths import PROJECT_ROOT


@contextmanager
def main_server(index: Path, imports: Path, structured: Path):
    environment = os.environ.copy()
    environment.update(
        PYTHON_DOTENV_DISABLED="1",
        MEDI_CHAT_INDEX_PATH=str(index),
        MEDI_CHAT_STRUCTURED_DIR=str(structured),
        MEDI_CHAT_IMPORT_DIR=str(imports),
    )
    environment.pop("MEDI_CHAT_DATABASE_URL", None)
    for key in (
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "ANTHROPIC_API_KEY",
        "TYPESAFE_API_KEY",
    ):
        environment[key] = ""
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    log_path = index.parent / f"owned-main-{port}.log"
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=PROJECT_ROOT,
            env=environment,
            stdout=log,
            stderr=log,
        )
        try:
            with httpx.Client(
                base_url=f"http://127.0.0.1:{port}", timeout=10
            ) as client:
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        break
                    try:
                        if client.get("/health").status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(0.05)
                else:
                    raise AssertionError(
                        "Owned main health timeout: "
                        + log_path.read_text(encoding="utf-8")
                    )
                yield client, process, log_path
        finally:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=15)
