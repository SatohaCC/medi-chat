import pytest
from backend.application.indexing.values import SearchSectionCode
from backend.application.retrieval.queries.models import SearchCriteria
from backend.application.retrieval.values import DetectionSource
from backend.infrastructure.persistence.postgres_runtime import PostgresRuntime
from backend.infrastructure.persistence.read_workers import ReadWorkers
from backend.tests.integration.test_postgres_registration import (
    pg_publisher as pg_publisher,
)
from backend.tests.integration.test_postgres_registration import publish
from backend.tests.support.postgres_fixtures import pg_engines as pg_engines
from backend.tests.support.registration_oracles import source


@pytest.mark.asyncio
async def test_tc094_empty_requested_products_cannot_search_all_active(pg_publisher):
    publish(pg_publisher, source("要求なしには返さない本文"))
    workers = ReadWorkers()
    try:
        async with PostgresRuntime(
            pg_publisher.engine, workers=workers
        ).acquire() as current:
            assert (
                await current.evidence_reader.search(
                    SearchCriteria(
                        source=DetectionSource.LOGIC,
                        section_codes=(SearchSectionCode("1"),),
                    ),
                    (),
                )
                == ()
            )
    finally:
        await workers.aclose()
