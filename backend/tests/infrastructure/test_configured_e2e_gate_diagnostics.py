import json
from tempfile import TemporaryFile
from unittest.mock import MagicMock

import pytest
from backend.config.database_settings import PostgresDatabaseSettings
from backend.infrastructure.cli.configured_e2e_gate import (
    _probe_failure,
    check_postgres_reachable,
    startup_log_diagnostics,
)
from backend.infrastructure.cli.configured_e2e_gate import (
    main as gate_main,
)
from backend.infrastructure.persistence.runtime.postgres_readiness import (
    verify_postgres_readiness,
)
from sqlalchemy.exc import OperationalError


def test_startup_failure_summary_includes_error_and_schema_code_without_traceback():
    log = """INFO: Waiting for application startup.
ERROR: Traceback (most recent call last):
  File \"backend/infrastructure/composition/app_lifespan.py\", line 12
RuntimeError: schema_not_ready: run explicit PostgreSQL migrations
ERROR: Application startup failed. Exiting.
"""

    assert startup_log_diagnostics(log) == [
        "RuntimeError: schema_not_ready: run explicit PostgreSQL migrations",
        "ERROR: Application startup failed. Exiting.",
    ]


def test_startup_failure_summary_redacts_credentials_tokens_and_queries():
    log = """ERROR: Failed to connect to postgresql://app:db-password@db/medi_chat?sslpassword=db-query-secret
RuntimeError: Authorization: Bearer secret-token
ValueError: api_key=private-key; question=patient query
"""

    diagnostics = startup_log_diagnostics(log)
    combined = "\n".join(diagnostics)

    assert "db-password" not in combined
    assert "db-query-secret" not in combined
    assert "secret-token" not in combined
    assert "private-key" not in combined
    assert "patient query" not in combined
    assert "[REDACTED]" in combined


def test_probe_failure_reads_and_includes_captured_startup_diagnostics():
    with TemporaryFile(mode="w+b") as log:
        log.write(b"RuntimeError: schema_not_ready: expected migration\n")
        error = _probe_failure("Configured main failed to start", log)

    assert "Configured main failed to start" in str(error)
    assert "RuntimeError: schema_not_ready: expected migration" in str(error)


def test_check_postgres_reachable_raises_environment_unavailable_on_unreachable_host():
    with pytest.raises(
        RuntimeError, match="environment_unavailable: PostgreSQL is not reachable"
    ) as exc_info:
        check_postgres_reachable(
            "postgresql://app:secret@127.0.0.1:59999/test", timeout=0.05
        )

    assert "docker compose --env-file .env.postgres up -d --wait" in str(exc_info.value)


def test_verify_postgres_readiness_identifies_connection_failure_as_environment_unavailable():
    engine = MagicMock()
    engine.connect.side_effect = OperationalError(
        "connection to server at '127.0.0.1', port 5432 failed: Connection refused",
        {},
        ConnectionRefusedError("Connection refused"),
    )

    with pytest.raises(
        RuntimeError, match="environment_unavailable: PostgreSQL connection refused"
    ) as exc_info:
        verify_postgres_readiness(engine)

    assert "docker compose --env-file .env.postgres up -d --wait" in str(exc_info.value)


def test_configured_e2e_gate_main_outputs_receipt_on_environment_unavailable(
    monkeypatch, capsys
):
    monkeypatch.setattr(
        "backend.infrastructure.cli.configured_e2e_gate.selected_settings",
        lambda: PostgresDatabaseSettings("postgresql://app:secret@127.0.0.1:5432/test"),
    )

    def failing_gate(*args, **kwargs):
        raise RuntimeError(
            "environment_unavailable: PostgreSQL is not reachable at 127.0.0.1:5432; "
            "start database with 'docker compose --env-file .env.postgres up -d --wait'"
        )

    monkeypatch.setattr(
        "backend.infrastructure.cli.configured_e2e_gate.run_gate", failing_gate
    )
    monkeypatch.setattr("sys.argv", ["configured_e2e_gate"])

    exit_code = gate_main()
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Configured gate failed: environment_unavailable:" in captured.out
    lines = [line for line in captured.out.splitlines() if line.strip()]
    receipt = json.loads(lines[1])
    assert receipt["backend"] == "postgresql"
    assert receipt["readiness"] == "environment_unavailable"
    assert receipt["reason"] == "connection_refused"
    assert "docker compose --env-file .env.postgres up -d --wait" in receipt["guide"]
