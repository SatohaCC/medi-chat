"""Owned process paused at an actual publisher boundary, killed by its test."""

import base64
import os
import sys
from pathlib import Path

from backend.infrastructure.persistence.registration.postgres_registration_publisher import (
    PostgresRegistrationPublisher,
)
from backend.infrastructure.persistence.runtime.postgres_engine import (
    create_postgres_engine,
)
from backend.infrastructure.pmda_xml.pmda_artifact_encoder import PmdaArtifactEncoder
from backend.infrastructure.pmda_xml.pmda_xml_decoder import PmdaXmlDecoder


def main():
    engine = create_postgres_engine(
        os.environ["TEST_RUNTIME_DATABASE_URL"], schema=os.environ["PG_WORKER_SCHEMA"]
    )

    def pause(phase):
        if phase == os.environ["PG_CRASH_PHASE"]:
            Path(os.environ["PG_CRASH_READY"]).write_text(phase, encoding="utf-8")
            sys.stdin.readline()
            raise AssertionError("Crash barrier unexpectedly resumed")

    raw = base64.b64decode(os.environ["PG_WORKER_SOURCE"])
    try:
        PostgresRegistrationPublisher(
            engine, encoder=PmdaArtifactEncoder(), fault=pause
        ).publish(PmdaXmlDecoder().decode(raw), raw)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
