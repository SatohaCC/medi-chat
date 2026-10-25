"""Owned real-PG original corpus for unittest public-contract suites."""

import os
from contextlib import contextmanager

from backend.infrastructure.persistence.registration.postgres_registration_publisher import (
    PostgresRegistrationPublisher,
)
from backend.infrastructure.pmda_xml.pmda_artifact_encoder import PmdaArtifactEncoder
from backend.infrastructure.pmda_xml.pmda_xml_decoder import PmdaXmlDecoder
from backend.tests.support.paths import PROJECT_ROOT
from backend.tests.support.postgres_fixtures import owned_postgres_engines


@contextmanager
def original_application_factory():
    from backend.main import create_app

    with owned_postgres_engines() as (owner, _, schema):
        publisher = PostgresRegistrationPublisher(owner, encoder=PmdaArtifactEncoder())
        for path in sorted((PROJECT_ROOT / "data/pmda/originals").glob("*/*.xml")):
            raw = path.read_bytes()
            publisher.publish(PmdaXmlDecoder().decode(raw), raw)

        def build(**kwargs):
            return create_app(
                database_url=os.environ["TEST_RUNTIME_DATABASE_URL"],
                _database_schema=schema,
                **kwargs,
            )

        yield build
