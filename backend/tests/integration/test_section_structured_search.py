"""Real XML section records survive SQLite indexing and keyword retrieval."""

import asyncio

from backend.application.medicine.product_models import ResolvedMedicine
from backend.domain.medicine.value_objects import MedicineMatch as DomainMedicineMatch
from backend.domain.retrieval.primitives import (
    DetectionSource,
    SearchKeyword,
    SearchSectionCode,
)
from backend.domain.retrieval.value_objects import SearchCriteria
from backend.infrastructure.persistence.evidence_reader import SqlAlchemyEvidenceReader
from backend.infrastructure.persistence.index_writer import SqlAlchemyIndexWriter
from backend.infrastructure.persistence.read_workers import ReadWorkers
from backend.infrastructure.persistence.sqlite_engine import create_sqlite_engine
from backend.infrastructure.pmda_xml.transform import transform
from backend.infrastructure.sources.file_index_source import FileIndexSourceReader
from backend.tests.infrastructure.persistence.test_alembic_migrations import (
    _migrate_database,
)
from backend.tests.support.paths import PROJECT_ROOT
from sqlalchemy.engine import URL


def test_generated_section_is_one_sqlite_hit_with_table_and_original_revision(tmp_path):
    source = (
        PROJECT_ROOT
        / "data/pmda/originals/イグザレルト錠２．５ｍｇ/630004_3339003F5020_1_08.xml"
    )
    structured = tmp_path / "structured"
    output = structured / source.stem
    validation = transform(source, output)
    index = tmp_path / "index.sqlite3"
    _migrate_database(index, structured)
    engine = create_sqlite_engine(
        URL.create("sqlite", database=str(index)).render_as_string(hide_password=False)
    )
    try:
        snapshot = FileIndexSourceReader(structured).read_snapshot()
        result = SqlAlchemyIndexWriter(engine).replace(snapshot)
        assert result.unit_count == validation["search_unit_count"] == 40
        medicines = (
            ResolvedMedicine(
                medicine=DomainMedicineMatch("", (), ("3339003F5020",), ()),
                document_ids=(source.stem,),
            ),
        )

        async def read():
            workers = ReadWorkers()
            try:
                reader = SqlAlchemyEvidenceReader(engine, workers=workers)
                whole = await reader.search(
                    SearchCriteria(
                        DetectionSource.LOGIC,
                        section_codes=(SearchSectionCode("10.1"),),
                    ),
                    medicines,
                )
                keyword = await reader.search(
                    SearchCriteria(
                        DetectionSource.KEYWORD, keywords=(SearchKeyword("リトナビル"),)
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
        payload = whole[0].to_dict()
        assert payload["unit_id"] == source.stem + ":10.1"
        assert "リトナビル" in whole[0].excerpt
        assert "<table>" in whole[0].excerpt
        assert whole[0].excerpt.count("<tr>") == 6
        assert payload["document_revision"] == {
            "source_label": "今回",
            "year_month": "2025-11",
            "version": "第8版",
        }
        assert source.stem + ":10.1" in {item.unit_id.value for item in keyword}
        assert len(adverse) == 1
        assert adverse[0].unit_id.value == source.stem + ":11.2"
        assert adverse[0].excerpt.count("<table>") == 1
        assert adverse[0].excerpt.count("<tr>") == 34
        assert "精神神経系" in adverse[0].excerpt
        assert "頻度不明" in adverse[0].excerpt
    finally:
        engine.dispose()
