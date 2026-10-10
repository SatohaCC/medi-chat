"""旧索引の移行前後で、保存値と実検索結果の一致を確認する。"""

import asyncio
import re
from dataclasses import dataclass
from pathlib import Path

from alembic.runtime.migration import MigrationContext
from sqlalchemy import MetaData, Table, select, text

from ...domain.attachment.value_objects import AttachmentProductMatch
from ...domain.retrieval.primitives import (
    DetectionSource,
    SearchKeyword,
    SearchSectionCode,
)
from ...domain.retrieval.value_objects import Evidence, SearchCriteria
from ...domain.shared.services import (
    normalize_match_text,
    normalize_search_text,
)
from ..json_payloads import parse_json_object
from . import schema
from .evidence_reader import SqlAlchemyEvidenceReader
from .medicine_reader import SqlAlchemyMedicineReader
from .read_workers import ReadWorkers
from .readonly_engine import create_readonly_engine


@dataclass(frozen=True)
class LegacyMigrationSnapshot:
    schema_objects: tuple[tuple[object, ...], ...]
    rows: dict[str, tuple[tuple[object, ...], ...]]
    criteria: tuple[SearchCriteria, ...]
    searches: tuple[tuple[Evidence, ...], ...]
    revisions: tuple[str, ...]


def _representative_criteria(
    unit_rows: tuple[tuple[object, ...], ...],
) -> tuple[SearchCriteria, ...]:
    chapter: SearchCriteria | None = None
    short: SearchCriteria | None = None
    fts: SearchCriteria | None = None
    for row in unit_rows:
        payload_json = row[4]
        if not isinstance(payload_json, str):
            raise ValueError("Invalid unit JSON during migration comparison")
        payload = parse_json_object(payload_json)
        section = payload.get("section")
        section_code = section.get("code") if isinstance(section, dict) else None
        if chapter is None and isinstance(section_code, str) and section_code:
            chapter = SearchCriteria(
                source=DetectionSource("logic"),
                section_codes=(SearchSectionCode(section_code),),
            )
        raw_text = payload.get("text")
        words = re.findall(r"\S+", raw_text) if isinstance(raw_text, str) else []
        for word in words:
            if short is None:
                fragment = next(
                    (
                        word[start : start + 2]
                        for start in range(len(word) - 1)
                        if len(normalize_match_text(word[start : start + 2])) == 2
                    ),
                    None,
                )
                if fragment is not None:
                    short = SearchCriteria(
                        source=DetectionSource("keyword"),
                        keywords=(SearchKeyword(fragment),),
                    )
            if fts is None:
                normalized = normalize_search_text(word)
                fragment = next(
                    (
                        normalized[:end]
                        for end in range(3, len(normalized) + 1)
                        if len(normalize_match_text(normalized[:end])) >= 3
                    ),
                    None,
                )
                if fragment is not None:
                    fts = SearchCriteria(
                        source=DetectionSource("keyword"),
                        keywords=(SearchKeyword(fragment),),
                    )
        if chapter is not None and short is not None and fts is not None:
            break
    return tuple(
        condition for condition in (chapter, short, fts) if condition is not None
    )


def read_legacy_migration_snapshot(
    index_path: Path, *, criteria: tuple[SearchCriteria, ...] | None = None
) -> LegacyMigrationSnapshot:
    engine = create_readonly_engine(index_path)
    try:
        with engine.connect() as connection:
            schema_objects = tuple(
                tuple(row)
                for row in connection.execute(
                    text(
                        "SELECT type, name, tbl_name, sql FROM sqlite_schema "
                        "WHERE tbl_name != 'alembic_version' ORDER BY type, name"
                    )
                )
            )
            rows: dict[str, tuple[tuple[object, ...], ...]] = {}
            for table_name in (
                *schema.metadata.tables,
                "unit_fts",
                "unit_fts_data",
                "unit_fts_idx",
                "unit_fts_content",
                "unit_fts_docsize",
                "unit_fts_config",
            ):
                table = schema.metadata.tables.get(table_name)
                if table is None:
                    table = Table(table_name, MetaData(), autoload_with=connection)
                rows[table_name] = tuple(
                    sorted(
                        (tuple(row) for row in connection.execute(select(table))),
                        key=repr,
                    )
                )
            revisions = MigrationContext.configure(connection).get_current_heads()
        if criteria is None:
            criteria = _representative_criteria(rows["units"])

        async def search() -> tuple[tuple[Evidence, ...], ...]:
            workers = ReadWorkers()
            try:
                medicines = await SqlAlchemyMedicineReader(
                    engine, workers=workers
                ).read_medicines()
                matches = (
                    AttachmentProductMatch(
                        generic_name="",
                        brand_names=[],
                        yj_codes=[],
                        document_ids=list(
                            dict.fromkeys(
                                medicine.document_id.value for medicine in medicines
                            )
                        ),
                    ),
                )
                reader = SqlAlchemyEvidenceReader(engine, workers=workers)
                return tuple(
                    [await reader.search(condition, matches) for condition in criteria]
                )
            finally:
                await workers.aclose()

        return LegacyMigrationSnapshot(
            schema_objects, rows, criteria, asyncio.run(search()), revisions
        )
    finally:
        engine.dispose()


def verify_legacy_migration(
    index_path: Path, before: LegacyMigrationSnapshot, expected_revision: str
) -> str:
    after = read_legacy_migration_snapshot(index_path, criteria=before.criteria)
    if (
        after.schema_objects != before.schema_objects
        or after.rows != before.rows
        or after.searches != before.searches
    ):
        raise ValueError(
            "Legacy migration verification failed: index contents or searches changed"
        )
    if after.revisions != (expected_revision,):
        raise ValueError(
            "Legacy migration verification failed: target revision mismatch"
        )
    return after.revisions[0]
