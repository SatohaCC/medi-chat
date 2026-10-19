"""Read-only configured PostgreSQL readiness and owned OS health probe."""

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.request import urlopen

from ...config.database_settings import (
    PostgresDatabaseSettings,
    resolve_postgres_database_settings,
)
from ...config.runtime_environment import load_runtime_environment
from ...project_paths import PROJECT_ROOT
from ..persistence.postgres_engine import create_postgres_engine
from ..persistence.postgres_readiness import verify_postgres_readiness


def terminate_owned(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
    else:
        process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def selected_settings() -> PostgresDatabaseSettings:
    load_runtime_environment()
    return resolve_postgres_database_settings()


def run_gate(
    settings: PostgresDatabaseSettings,
    *,
    port: int = 3212,
    timeout: float = 30,
    schema: str = "public",
) -> dict:
    engine = create_postgres_engine(settings.database_url, schema=schema)
    try:
        verify_postgres_readiness(engine)
    finally:
        engine.dispose()
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            raise RuntimeError(
                f"Dedicated probe port {port} is occupied; existing server is unchanged"
            ) from None
    environment = {
        **os.environ,
        "MEDI_CHAT_DATABASE_URL": settings.database_url,
        "MEDI_CHAT_DATABASE_SCHEMA": schema,
        "PYTHONUTF8": "1",
        "PYTHON_DOTENV_DISABLED": "1",
    }
    with tempfile.TemporaryFile(mode="w+b") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.infrastructure.composition.configured_probe:create_probe",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=PROJECT_ROOT,
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(
                        "Configured main failed to start; verify PostgreSQL readiness and configuration"
                    )
                try:
                    with urlopen(
                        f"http://127.0.0.1:{port}/health", timeout=1
                    ) as response:
                        health = json.load(response)
                    if health.get("status") == "ok":
                        return {
                            "backend": "postgresql",
                            "readiness": "passed",
                            "os_health": health,
                            "pid": process.pid,
                            "port": port,
                        }
                except URLError, TimeoutError, ConnectionError:
                    pass
                time.sleep(0.1)
            raise RuntimeError("Configured OS health timed out")
        finally:
            terminate_owned(process)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=3212)
    parser.add_argument("--resolve-only", action="store_true")
    args = parser.parse_args()
    try:
        settings = selected_settings()
        print(json.dumps({"backend": "postgresql"}), flush=True)
        if not args.resolve_only:
            print(
                json.dumps(run_gate(settings, port=args.port), ensure_ascii=False),
                flush=True,
            )
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"Configured gate failed: {exc}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
