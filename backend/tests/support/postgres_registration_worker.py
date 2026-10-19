"""Owned subprocess for PG-016: release both writers after transformation."""

import base64
import json
import os
import sys

from backend.application.attachment_import.import_errors import ImportConflict
from backend.infrastructure.persistence.postgres_engine import create_postgres_engine
from backend.infrastructure.persistence.postgres_registration import (
    PostgresRegistrationPublisher,
)
from backend.infrastructure.pmda_xml.artifact_mapping import PmdaArtifactEncoder
from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder
from sqlalchemy import event


def main():
    engine = create_postgres_engine(
        os.environ["TEST_RUNTIME_DATABASE_URL"], schema=os.environ["PG_WORKER_SCHEMA"]
    )
    pids = set()

    @event.listens_for(engine, "before_cursor_execute")
    def observe(connection, cursor, statement, parameters, context, executemany):
        pids.add(connection.connection.driver_connection.info.backend_pid)

    def fault(phase):
        if phase == "prepared":
            print("prepared", flush=True)
            if sys.stdin.readline().strip() != "go":
                raise RuntimeError("Missing parent barrier release")

    raw = base64.b64decode(os.environ["PG_WORKER_SOURCE"])
    publisher = PostgresRegistrationPublisher(
        engine, encoder=PmdaArtifactEncoder(), fault=fault
    )
    try:
        result = publisher.publish(PmdaXmlDecoder().decode(raw), raw)
        output = {
            "status": "ok",
            "sequence": result.registration_sequence,
            "reused": result.reused,
            "sha256": result.source_sha256,
            "generation": result.generation_id,
        }
    except ImportConflict as error:
        output = {"status": "conflict", "code": error.code}
    finally:
        engine.dispose()
    print(json.dumps({**output, "pids": sorted(pids)}), flush=True)


if __name__ == "__main__":
    main()
