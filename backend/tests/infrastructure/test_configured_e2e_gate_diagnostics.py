from tempfile import TemporaryFile

from backend.infrastructure.cli.configured_e2e_gate import (
    _probe_failure,
    startup_log_diagnostics,
)


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
