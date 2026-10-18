"""Read-only configured startup gate for the normal E2E entry point."""

import argparse
import json
import os
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from ...config.database_settings import DatabaseSettings, resolve_database_settings
from ...config.runtime_environment import load_runtime_environment
from ...project_paths import PROJECT_ROOT
from ..composition.index_verifier import verify_index_readiness
from ..composition.recovery_readiness import verify_no_recovery_work


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


def selected_settings() -> DatabaseSettings:
    load_runtime_environment()
    return resolve_database_settings()


def run_gate(
    settings: DatabaseSettings, *, port: int = 3212, timeout: float = 30
) -> dict:
    verify_index_readiness(settings.structured_dir, settings.index_path)
    verify_no_recovery_work(settings.index_path)
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            raise RuntimeError(
                f"Dedicated probe port {port} is occupied; existing server is unchanged"
            ) from None
    environment = dict(os.environ)
    environment["MEDI_CHAT_STRUCTURED_DIR"] = str(settings.structured_dir)
    environment["MEDI_CHAT_INDEX_PATH"] = str(settings.index_path)
    environment["MEDI_CHAT_DATABASE_URL"] = settings.database_url
    with tempfile.TemporaryDirectory(prefix="medi-chat-configured-smoke-") as temporary:
        environment["MEDI_CHAT_IMPORT_DIR"] = str(Path(temporary) / "imports")
        with tempfile.TemporaryFile(mode="w+b") as log:
            process = subprocess.Popen(
                [
                    "uv",
                    "run",
                    "--project",
                    str(PROJECT_ROOT / "backend"),
                    "--locked",
                    "uvicorn",
                    "--app-dir",
                    str(PROJECT_ROOT),
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
                        log.seek(0)
                        raise RuntimeError(
                            "Configured main failed to start: "
                            + log.read().decode("utf-8", errors="replace")
                        )
                    try:
                        with urlopen(
                            f"http://127.0.0.1:{port}/health", timeout=1
                        ) as response:
                            health = json.load(response)
                        if health.get("status") == "ok":
                            return {
                                "structured_dir": str(settings.structured_dir),
                                "index_path": str(settings.index_path),
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
        print(
            json.dumps(
                {
                    "structured_dir": str(settings.structured_dir),
                    "index_path": str(settings.index_path),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
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
