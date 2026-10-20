"""大項目データの実保存・再起動・PostgreSQL snapshot検索を検証する。"""

import pytest
from backend.application.medicine.product_catalog import MedicineCatalog
from backend.domain.medicine.identifiers import YjCode
from backend.domain.retrieval.primitives import (
    DetectionSource,
    SearchKeyword,
    SearchSectionCode,
)
from backend.domain.retrieval.value_objects import SearchCriteria
from backend.infrastructure.persistence import postgres_schema as schema
from backend.infrastructure.persistence.postgres_engine import create_postgres_engine
from backend.infrastructure.persistence.postgres_runtime import PostgresRuntime
from backend.infrastructure.persistence.read_workers import ReadWorkers
from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder
from backend.tests.integration.test_postgres_registration import (
    pg_publisher as pg_publisher,
)
from backend.tests.support.attachment_import_fixtures import xml_source
from backend.tests.support.postgres_fixtures import pg_engines as pg_engines
from sqlalchemy import select


@pytest.mark.asyncio
@pytest.mark.parametrize("requested", ["10", "10.1", "10.2"])
async def test_saved_major_section_keeps_children_after_restart_and_search(
    pg_engines, pg_publisher, requested
):
    source = xml_source(
        "<Interactions><ContraIndicatedCombinations><Detail><Lang>禁忌の対象薬剤</Lang>"
        "</Detail></ContraIndicatedCombinations><PrecautionsForCombinations><Detail>"
        "<Lang>注意の対象薬剤</Lang></Detail></PrecautionsForCombinations></Interactions>"
    )
    result = pg_publisher.publish(PmdaXmlDecoder().decode(source), source)
    with pg_engines[0].connect() as connection:
        stored = connection.execute(select(schema.versions)).mappings().one()
    assert stored["source"] == source
    saved = stored["structure"]["document"]
    assert [section["code"] for section in saved["sections"]] == ["10"]
    assert [child["code"] for child in saved["sections"][0]["children"]] == [
        "10.1",
        "10.2",
    ]
    assert result.section_count == result.search_unit_count == 1
    # New engine/runtime restore only persisted Domain structure, no reused decoder.
    workers = ReadWorkers()
    engine = create_postgres_engine(
        pg_engines[1].url.render_as_string(hide_password=False), schema=pg_engines[2]
    )
    runtime = PostgresRuntime(engine, workers=workers)
    try:
        async with runtime.acquire() as snapshot:
            catalog = MedicineCatalog(await snapshot.medicine_reader.read_medicines())
            medicines = tuple(catalog.match_yj_codes((YjCode("111111111111"),)))
            for reader in (snapshot.evidence_reader,):
                for keywords in ((), (SearchKeyword("対象薬剤"),)):
                    evidence = await reader.search(
                        SearchCriteria(
                            source=DetectionSource.LOGIC,
                            section_codes=(SearchSectionCode(requested),),
                            keywords=keywords,
                        ),
                        medicines,
                    )
                    assert {item.section["code"] for item in evidence} == {"10"}
                    assert len({item.unit_id for item in evidence}) == 1
                    for item in evidence:
                        assert "禁忌の対象薬剤" in item.excerpt
                        assert "注意の対象薬剤" in item.excerpt
                        assert "10.1" in item.excerpt and "10.2" in item.excerpt
                for absent in ("1", "10.3"):
                    assert (
                        await reader.search(
                            SearchCriteria(
                                source=DetectionSource.LOGIC,
                                section_codes=(SearchSectionCode(absent),),
                            ),
                            medicines,
                        )
                        == ()
                    )
    finally:
        await workers.aclose()
        engine.dispose()
