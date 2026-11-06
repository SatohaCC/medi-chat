"""Read-only configured PostgreSQL readiness and owned OS health probe."""

import argparse
import errno
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
from typing import Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen

from sqlalchemy.engine import make_url

from backend.config.authentication_settings import read_authentication_settings
from backend.config.database_settings import (
    PostgresDatabaseSettings,
    resolve_postgres_database_settings,
)
from backend.config.runtime_environment import load_runtime_environment
from backend.domain.identity.identifiers import UserId
from backend.infrastructure.authentication.access_refresh_tokens import JwtTokens
from backend.infrastructure.persistence.runtime.postgres_engine import (
    create_postgres_engine,
)
from backend.infrastructure.persistence.runtime.postgres_readiness import (
    verify_postgres_readiness,
)
from backend.project_paths import PROJECT_ROOT

_ERROR_LINE = re.compile(r"\b(?:ERROR|CRITICAL):", re.IGNORECASE)
_EXCEPTION_LINE = re.compile(r"^\s*[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*(?:Error|Exception):")
_LOCAL_DATABASE_HOSTS = {"localhost", "127.0.0.1", "::1"}
_LOCAL_DATABASE_GUIDE = "docker compose --env-file .env.postgres up -d --wait"


class EnvironmentUnavailable(RuntimeError):
    def __init__(self, reason: str, host: str, port: int) -> None:
        self.reason = reason
        self.host = host
        self.port = port
        self.guide = (
            _LOCAL_DATABASE_GUIDE
            if reason == "connection_refused" and host.lower() in _LOCAL_DATABASE_HOSTS
            else None
        )
        message = (
            f"environment_unavailable: {reason}: PostgreSQL is not reachable "
            f"at {host}:{port}"
        )
        if self.guide:
            message += f"; start database with '{self.guide}'"
        super().__init__(message)


class _ReadableBinaryLog(Protocol):
    def flush(self) -> None: ...

    def seek(self, target: int, whence: int = 0, /) -> int: ...

    def read(self, n: int = -1, /) -> bytes: ...


def _redact_startup_log_line(line: str) -> str:
    line = re.sub(
        r"\b((?:postgres(?:ql)?(?:\+\w+)?|mysql(?:\+\w+)?|redis(?:\+\w+)?)://)[^/\s:@]+:[^@\s/]+@",
        r"\1[REDACTED]@",
        line,
        flags=re.IGNORECASE,
    )
    line = re.sub(
        r"([\"']?\b(?:proxy-)?authorization\b[\"']?\s*[:=]\s*)[^\r\n]*",
        r"\1[REDACTED]",
        line,
        flags=re.IGNORECASE,
    )
    line = re.sub(r"\bBearer\s+\S+", "Bearer [REDACTED]", line, flags=re.IGNORECASE)
    line = re.sub(
        r"([\"']?\b(?:search[_-]?query|query|question)\b[\"']?\s*[=:]\s*)(?:\"[^\"]*\"|'[^']*'|[^\r\n]*)",
        r"\1[REDACTED]",
        line,
        flags=re.IGNORECASE,
    )
    line = re.sub(
        r"([\"']?\b[A-Za-z0-9_-]*[_-]?(?:access[_-]?token|refresh[_-]?token|api[_-]?key|client[_-]?secret|private[_-]?key|secret[_-]?key|password|secret|token)\b[\"']?\s*[=:]\s*)(?:\"[^\"]*\"|'[^']*'|[^&\s,;]+)",
        r"\1[REDACTED]",
        line,
        flags=re.IGNORECASE,
    )
    return re.sub(
        r"((?:https?://|postgres(?:ql)?(?:\+\w+)?://|mysql(?:\+\w+)?://|redis(?:\+\w+)?://|/)[^\s\"'<>?]+)\?[^\s\"'<>]*",
        r"\1?[REDACTED]",
        line,
        flags=re.IGNORECASE,
    )


def startup_log_diagnostics(contents: str) -> list[str]:
    """Return a short, redacted error summary without traceback or request logs."""
    diagnostics = []
    for line in contents.splitlines():
        if "Traceback (most recent call last)" in line:
            continue
        if not _ERROR_LINE.search(line) and not _EXCEPTION_LINE.search(line):
            continue
        summary = _redact_startup_log_line(line).strip()[:500]
        if summary and summary not in diagnostics:
            diagnostics.append(summary)
    return diagnostics[-6:]


def _captured_startup_diagnostics(log: _ReadableBinaryLog) -> list[str]:
    log.flush()
    log.seek(0)
    return startup_log_diagnostics(log.read().decode("utf-8", errors="replace"))


def _probe_failure(message: str, log: _ReadableBinaryLog) -> RuntimeError:
    diagnostics = _captured_startup_diagnostics(log)
    if diagnostics:
        message += "\nStartup diagnostics:\n" + "\n".join(diagnostics)
    return RuntimeError(message)


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


def check_postgres_reachable(database_url: str, *, timeout: float = 1.0) -> None:
    """Fast socket probe to check if the database host is reachable before running queries."""
    url = make_url(database_url)
    host = url.host or "127.0.0.1"
    port = url.port or 5432
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
    except socket.gaierror as exc:
        raise EnvironmentUnavailable("name_resolution_failed", host, port) from exc
    except TimeoutError as exc:
        raise EnvironmentUnavailable("connection_timeout", host, port) from exc
    except OSError as exc:
        if exc.errno == errno.ECONNREFUSED:
            reason = "connection_refused"
        elif exc.errno in {errno.EHOSTUNREACH, errno.ENETUNREACH}:
            reason = "network_unreachable"
        else:
            reason = "connection_error"
        raise EnvironmentUnavailable(reason, host, port) from exc


def run_gate(
    settings: PostgresDatabaseSettings,
    *,
    port: int = 3212,
    timeout: float = 30,
    schema: str = "public",
) -> dict:
    check_postgres_reachable(settings.database_url)
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
    auth = read_authentication_settings()
    now = int(time.time())
    token = JwtTokens(
        private_key=auth.private_key.get_secret_value(),
        public_keys=auth.public_keys,
        key_id=auth.key_id,
        issuer=auth.issuer,
        audience=auth.audience,
    ).issue(str(UserId.generate()), now, now + 300)
    headers = {"Cookie": "medi_chat_access_token=" + token}
    with tempfile.TemporaryFile(mode="w+b") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "--no-proxy-headers",
                "backend.infrastructure.cli.configured_probe:create_probe",
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
                    raise _probe_failure(
                        "Configured main failed to start; verify PostgreSQL readiness and configuration",
                        log,
                    )
                try:
                    with urlopen(
                        Request(f"http://127.0.0.1:{port}/health", headers=headers),
                        timeout=1,
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
            raise _probe_failure("Configured OS health timed out", log)
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
        if isinstance(exc, EnvironmentUnavailable):
            print(
                json.dumps(
                    {
                        "backend": "postgresql",
                        "readiness": "environment_unavailable",
                        "reason": exc.reason,
                        **({"guide": exc.guide} if exc.guide else {}),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
        print(f"Configured gate failed: {exc}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
