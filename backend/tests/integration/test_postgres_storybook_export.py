"""Development evidence export uses the normal public PG snapshot contract."""

import runpy

import pytest
from backend.domain.medicine.identifiers import YjCode
from backend.domain.medicine.primitives import BrandName, MatchedAlias
from backend.tests.support.paths import PROJECT_ROOT
from backend.tests.support.postgres_fixtures import pg_api as pg_api
from backend.tests.support.postgres_fixtures import pg_engines as pg_engines
from backend.tests.support.postgres_observations import digest


@pytest.mark.asyncio
async def test_pg038_storybook_export_is_readonly_and_returns_public_evidence(
    pg_api, pg_engines
):
    import os

    from backend.application.indexing.search_values import SearchSectionCode
    from backend.application.medicine.product_models import ResolvedMedicine
    from backend.application.retrieval.search_models import SearchCriteria
    from backend.application.retrieval.search_values import DetectionSource
    from backend.domain.medicine.value_objects import MedicineMatch
    from backend.presentation.chat_dto_mapper import evidence_to_api

    app = pg_api()
    async with (
        app.router.lifespan_context(app),
        app.state.generation_runtime.acquire() as snapshot,
    ):
        evidence = await snapshot.evidence_reader.search(
            SearchCriteria(
                source=DetectionSource.LOGIC,
                section_codes=(SearchSectionCode("11"),),
            ),
            (
                ResolvedMedicine(
                    medicine=MedicineMatch(
                        generic_name=None,
                        brand_names=tuple(BrandName(value) for value in ()),
                        yj_codes=tuple(YjCode(value) for value in ("1234567A0000",)),
                        matched_aliases=tuple(MatchedAlias(value) for value in ()),
                    ),
                    document_ids=("test_001",),
                ),
            ),
        )
    expected = [evidence_to_api(item).model_dump(mode="json") for item in evidence]
    assert len(expected) == 1 and "記載2" in expected[0]["excerpt"]
    before = digest(pg_engines[0])
    exporter = runpy.run_path(
        str(PROJECT_ROOT / "frontend/scripts/export-storybook-evidence.py")
    )
    actual = await exporter["read_evidence"](
        os.environ["TEST_RUNTIME_DATABASE_URL"], pg_engines[2]
    )
    assert actual == expected
    assert digest(pg_engines[0]) == before
