import pytest
from backend.domain.retrieval.primitives import DetectionSource, SearchSectionCode
from backend.domain.retrieval.value_objects import SearchCriteria
from backend.infrastructure.persistence.generation_runtime import GenerationRuntime
from backend.infrastructure.persistence.read_workers import ReadWorkers
from backend.tests.test_registration_publisher import publish, source
from backend.tests.test_registration_publisher import publisher as publisher


@pytest.mark.asyncio
async def test_tc094_empty_requested_products_cannot_search_all_active(publisher):
    publish(publisher, source("要求なしには返さない本文"))
    workers = ReadWorkers()
    try:
        async with GenerationRuntime(publisher, workers=workers).acquire() as current:
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
