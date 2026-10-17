"""実際のSQLite索引を使うテストのデータ準備。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from backend.infrastructure.persistence.index_reader import SqlAlchemyIndexReader
from backend.infrastructure.persistence.index_writer import SqlAlchemyIndexWriter
from backend.infrastructure.persistence.sqlite_engine import create_sqlite_engine
from backend.infrastructure.sources.file_index_source import FileIndexSourceReader
from sqlalchemy.engine import URL


@dataclass(frozen=True)
class BuiltIndex:
    index_stats: dict[str, int]


def build_document_store(structured_dir: Path, index_path: Path) -> BuiltIndex:
    from backend.tests.infrastructure.persistence.test_alembic_migrations import (
        _migrate_database,
    )

    _migrate_database(index_path, structured_dir)
    engine = create_sqlite_engine(
        URL.create("sqlite", database=index_path.as_posix()).render_as_string(
            hide_password=False
        )
    )
    try:
        SqlAlchemyIndexWriter(engine).replace(
            FileIndexSourceReader(structured_dir).read_snapshot()
        )
        return BuiltIndex(SqlAlchemyIndexReader(engine)._read_index_stats())
    finally:
        engine.dispose()


def write_structured_document(root: Path, unit_count: int = 3) -> Path:
    structured_dir = root / "structured"
    document_dir = structured_dir / "test_001"
    document_dir.mkdir(parents=True)
    document = {
        "document": {
            "company_identifier": "test",
            "package_insert_no": "001",
            "generic_name": "テスト成分",
            "products": [{"yj_code": "1234567A0000", "brand_name": "テスト薬"}],
        },
        "source": {"pmda_url": "https://example.test/package-insert"},
    }
    units = [
        {
            "unit_id": f"test_001:{index:03d}",
            "document_key": "test_001",
            "product_yj_codes": ["1234567A0000"],
            "section": {"code": "11.1", "title": "重大な副作用"},
            "kind": "text",
            "text": f"頭痛に注意してください。記載{index}",
        }
        for index in range(unit_count)
    ]
    (document_dir / "document.json").write_text(
        json.dumps(document, ensure_ascii=False), encoding="utf-8"
    )
    (document_dir / "search_units.jsonl").write_text(
        "\n".join(json.dumps(unit, ensure_ascii=False) for unit in units),
        encoding="utf-8",
    )
    return structured_dir
