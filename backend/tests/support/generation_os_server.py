"""Own one actual main process/port. Never stop an existing server."""

import os
import socket
import subprocess
import sys
import time
from contextlib import contextmanager, suppress
from pathlib import Path

import httpx
import psutil
from backend.tests.support.authentication import signed_test_headers
from backend.tests.support.paths import PROJECT_ROOT
from backend.tests.support.postgres_fixtures import validate_test_database_url


@contextmanager
def main_server(schema: str, root: Path, *, performance: bool = False):
    validate_test_database_url(os.environ["TEST_RUNTIME_DATABASE_URL"], runtime=True)
    environment = os.environ.copy()
    environment.update(
        PYTHON_DOTENV_DISABLED="1",
        MEDI_CHAT_DATABASE_URL=os.environ["TEST_RUNTIME_DATABASE_URL"],
        PG_WORKER_SCHEMA=schema,
    )
    if performance:
        environment["PG_PERF_DIRECTORY"] = str(root)
    for key in (
        "MEDI_CHAT_INDEX_PATH",
        "MEDI_CHAT_STRUCTURED_DIR",
        "MEDI_CHAT_IMPORT_DIR",
    ):
        environment.pop(key, None)
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
    log_path = root / f"owned-main-{port}.log"
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                (
                    "backend.tests.support.postgres_performance_server:create_server"
                    if performance
                    else "backend.tests.support.postgres_application_server:create_server"
                ),
                "--factory",
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
                base_url=f"http://127.0.0.1:{port}",
                timeout=10,
                headers=signed_test_headers(),
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
            # Windows venv python.exe can be a launcher owning the real interpreter.
            # Capture only this child's descendants before stopping that launcher.
            try:
                descendants = psutil.Process(process.pid).children(recursive=True)
            except psutil.NoSuchProcess:
                descendants = []
            for descendant in reversed(descendants):
                with suppress(psutil.NoSuchProcess):
                    descendant.terminate()
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=15)
            _, alive = psutil.wait_procs(descendants, timeout=15)
            assert not alive, "Owned interpreter descendants must exit"
