"""Actual GC process held at its acquired row lock for the PG-046 topology."""

import json
import os
import time
from pathlib import Path

from backend.infrastructure.persistence.postgres_engine import create_postgres_engine
from backend.infrastructure.persistence.postgres_registration import (
    PostgresRegistrationPublisher,
)
from backend.infrastructure.pmda_xml.artifact_mapping import PmdaArtifactEncoder
from sqlalchemy import text


def main():
    directory = Path(os.environ["PG_PERF_DIRECTORY"])
    engine = create_postgres_engine(
        os.environ["TEST_RUNTIME_DATABASE_URL"], schema=os.environ["PG_WORKER_SCHEMA"]
    )
    with engine.connect() as connection:
        pid = connection.execute(text("SELECT pg_backend_pid()")).scalar_one()
    (directory / "maintenance-ready.json").write_text(
        json.dumps({"backend_pid": pid}), encoding="utf-8"
    )

    def fault(phase):
        if phase == "cleanup":
            (directory / "maintenance-lock-held").write_text("held", encoding="utf-8")
            deadline = time.monotonic() + 20
            while not (directory / "release-maintenance-lock").exists():
                if time.monotonic() > deadline:
                    raise RuntimeError("Maintenance topology barrier timed out")
                time.sleep(0.002)

    try:
        while not (directory / "release-maintenance-worker").exists():
            time.sleep(0.002)
        started = time.time()
        PostgresRegistrationPublisher(
            engine, encoder=PmdaArtifactEncoder(), fault=fault
        ).cleanup()
        (directory / "maintenance-summary.json").write_text(
            json.dumps({"backend_pid": pid, "start": started, "end": time.time()}),
            encoding="utf-8",
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
