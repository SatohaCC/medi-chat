"""Real XML section records survive PostgreSQL storage and keyword retrieval."""

import asyncio

import pytest
from backend.application.indexing.search_values import SearchSectionCode
from backend.application.medicine.product_models import ResolvedMedicine
from backend.application.retrieval.evidence_payloads import evidence_payload
from backend.application.retrieval.search_models import SearchCriteria
from backend.application.retrieval.search_values import DetectionSource, SearchKeyword
from backend.domain.medicine.identifiers import YjCode
from backend.domain.medicine.primitives import BrandName, MatchedAlias
from backend.domain.medicine.value_objects import MedicineMatch as DomainMedicineMatch
from backend.infrastructure.persistence.postgres_runtime import PostgresRuntime
from backend.infrastructure.persistence.read_workers import ReadWorkers
from backend.tests.integration.test_postgres_registration import (
    pg_publisher as pg_publisher,
)
from backend.tests.integration.test_postgres_registration import publish
from backend.tests.support.paths import PROJECT_ROOT
from backend.tests.support.postgres_fixtures import pg_engines as pg_engines

pytestmark = pytest.mark.source_data


def test_generated_section_is_one_postgres_hit_with_table_and_original_revision(
    pg_publisher,
):
    source = (
        PROJECT_ROOT
        / "data/pmda/originals/イグザレルト錠２．５ｍｇ/630004_3339003F5020_1_08.xml"
    )
    receipt = publish(pg_publisher, source.read_bytes())
    assert receipt.search_unit_count == 22
    try:
        medicines = (
            ResolvedMedicine(
                medicine=DomainMedicineMatch(
                    generic_name=None,
                    brand_names=tuple(BrandName(value) for value in ()),
                    yj_codes=tuple(YjCode(value) for value in ("3339003F5020",)),
                    matched_aliases=tuple(MatchedAlias(value) for value in ()),
                ),
                document_ids=(source.stem,),
            ),
        )

        async def read():
            workers = ReadWorkers()
            try:
                async with PostgresRuntime(
                    pg_publisher.engine, workers=workers
                ).acquire() as snapshot:
                    reader = snapshot.evidence_reader
                    whole = await reader.search(
                        SearchCriteria(
                            DetectionSource.LOGIC,
                            section_codes=(SearchSectionCode("10.1"),),
                        ),
                        medicines,
                    )
                    keyword = await reader.search(
                        SearchCriteria(
                            DetectionSource.KEYWORD,
                            keywords=(SearchKeyword("リトナビル"),),
                        ),
                        medicines,
                    )
                    adverse = await reader.search(
                        SearchCriteria(
                            DetectionSource.LOGIC,
                            section_codes=(SearchSectionCode("11.2"),),
                        ),
                        medicines,
                    )
                    return whole, keyword, adverse
            finally:
                await workers.aclose()

        whole, keyword, adverse = asyncio.run(read())
        assert len(whole) == 1
        payload = evidence_payload(whole[0])
        assert payload["unit_id"] == f"{source.stem}:{receipt.source_sha256}:10"
        assert "リトナビル" in whole[0].excerpt.value
        assert "<table>" in whole[0].excerpt.value
        assert whole[0].excerpt.value.count("<tr>") == 15
        assert payload["document_revision"] == {
            "source_label": "今回",
            "year_month": "2025-11",
            "version": "第8版",
        }
        assert f"{source.stem}:{receipt.source_sha256}:10" in {
            item.unit_id.value for item in keyword
        }
        assert len(adverse) == 1
        assert adverse[0].unit_id.value == f"{source.stem}:{receipt.source_sha256}:11"
        assert adverse[0].excerpt.value.count("<table>") == 1
        assert adverse[0].excerpt.value.count("<tr>") == 34
        assert "精神神経系" in adverse[0].excerpt.value
        assert "頻度不明" in adverse[0].excerpt.value
    finally:
        assert pg_publisher.engine.pool.checkedout() == 0
