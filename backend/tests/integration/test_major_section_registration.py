"""大項目データの実保存・再起動・SQLite/世代検索を検証する。"""

import json

import pytest
from backend.application.medicine.product_catalog import MedicineCatalog
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.retrieval.primitives import (
    DetectionSource,
    SearchKeyword,
    SearchSectionCode,
)
from backend.domain.retrieval.value_objects import SearchCriteria
from backend.infrastructure.persistence.attachment_import_store import (
    FileAttachmentImportStore,
)
from backend.infrastructure.persistence.evidence_reader import SqlAlchemyEvidenceReader
from backend.infrastructure.persistence.generation_runtime import GenerationRuntime
from backend.infrastructure.persistence.read_workers import ReadWorkers
from backend.infrastructure.persistence.registration_publisher import (
    SqliteRegistrationPublisher,
)
from backend.infrastructure.persistence.sqlite_engine import create_sqlite_engine
from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder
from backend.tests.infrastructure.persistence.test_alembic_migrations import (
    _migrate_database,
)
from backend.tests.support.attachment_import_fixtures import xml_source


@pytest.mark.asyncio
@pytest.mark.parametrize("requested", ["10", "10.1", "10.2"])
async def test_saved_major_section_keeps_children_after_restart_and_search(
    tmp_path, requested
):
    source = xml_source(
        "<Interactions><ContraIndicatedCombinations><Detail><Lang>禁忌の対象薬剤</Lang>"
        "</Detail></ContraIndicatedCombinations><PrecautionsForCombinations><Detail>"
        "<Lang>注意の対象薬剤</Lang></Detail></PrecautionsForCombinations></Interactions>"
    )
    index = tmp_path / "index.sqlite3"
    _migrate_database(index, tmp_path)
    store = FileAttachmentImportStore(tmp_path / "imports")
    publisher = SqliteRegistrationPublisher(index, store)
    result = publisher.publish(PmdaXmlDecoder().decode(source), source)
    directory = store._target(DocumentId(result.document_id), result.source_sha256)
    assert (directory / "source.xml").read_bytes() == source
    saved = json.loads((directory / "document.json").read_bytes())
    assert [section["code"] for section in saved["sections"]] == ["10"]
    assert [child["code"] for child in saved["sections"][0]["children"]] == [
        "10.1",
        "10.2",
    ]
    assert result.section_count == result.search_unit_count == 1
    # Recreate the readers and publisher from persisted files, with no reused decoder/model.
    publisher = SqliteRegistrationPublisher(
        index, FileAttachmentImportStore(tmp_path / "imports")
    )
    workers = ReadWorkers()
    runtime = GenerationRuntime(publisher, workers=workers)
    engine = create_sqlite_engine(f"sqlite:///{index.as_posix()}")
    sql_reader = SqlAlchemyEvidenceReader(engine, workers=workers)
    try:
        async with runtime.acquire() as snapshot:
            catalog = MedicineCatalog(await snapshot.medicine_reader.read_medicines())
            medicines = tuple(catalog.resolve_medicines("", ["111111111111"]))
            for reader in (snapshot.evidence_reader, sql_reader):
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
