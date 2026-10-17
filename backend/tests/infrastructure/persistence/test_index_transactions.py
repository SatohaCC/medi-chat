"""実Core writerの部分書込みを失敗させ、別接続でrollbackを確認する。"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from backend.application.indexing.index_models import IndexBuildResult
from backend.application.medicine.product_models import ResolvedMedicine
from backend.domain.medicine.value_objects import MedicineMatch as DomainMedicineMatch
from backend.domain.retrieval.primitives import (
    DetectionSource,
    SearchKeyword,
    SearchSectionCode,
)
from backend.domain.retrieval.value_objects import Evidence, SearchCriteria
from backend.infrastructure.persistence import schema
from backend.infrastructure.persistence.evidence_reader import SqlAlchemyEvidenceReader
from backend.infrastructure.persistence.index_writer import SqlAlchemyIndexWriter
from backend.infrastructure.persistence.sqlite_engine import create_sqlite_engine
from backend.infrastructure.sources.file_index_source import FileIndexSourceReader
from backend.tests.infrastructure.persistence.test_alembic_migrations import (
    _snapshot_existing_database,
)
from backend.tests.infrastructure.persistence.test_package_insert_index import (
    migrated_index as migrated_index,
)
from sqlalchemy import event
from sqlalchemy.engine import Connection, Engine, ExecutionContext
from sqlalchemy.sql.dml import Insert


class InjectedBuildFailure(RuntimeError):
    """DB書込み境界から返すテスト専用の失敗。"""


def _search_results(engine: Engine) -> tuple[tuple[Evidence, ...], ...]:
    reader = SqlAlchemyEvidenceReader(engine)
    medicines = (
        ResolvedMedicine(
            medicine=DomainMedicineMatch(
                generic_name="テスト成分",
                brand_names=("テスト薬",),
                yj_codes=("1234567A0000",),
            ),
            document_ids=("test_001",),
        ),
    )
    return tuple(
        asyncio.run(reader.search(criteria, medicines))
        for criteria in (
            SearchCriteria(
                source=DetectionSource("logic"),
                section_codes=(SearchSectionCode("11.1"),),
            ),
            SearchCriteria(
                source=DetectionSource("keyword"), keywords=(SearchKeyword("頭痛"),)
            ),
            SearchCriteria(
                source=DetectionSource("keyword"), keywords=(SearchKeyword("注意して"),)
            ),
        )
    )


@pytest.mark.parametrize("failure_phase", ["normal_data", "partial_fts", "fingerprint"])
def test_partial_build_rolls_back_all_index_data(
    migrated_index: tuple[Path, Engine], failure_phase: str
) -> None:
    source, engine = migrated_index
    writer = SqlAlchemyIndexWriter(engine)
    initial = FileIndexSourceReader(source).read_snapshot()
    assert writer.replace(initial) == IndexBuildResult(1, 3)
    index_path = Path(engine.url.database or "")
    expected = _snapshot_existing_database(index_path)
    before_search = _search_results(engine)
    assert all(len(result) == 3 for result in before_search)
    assert expected.revision is not None and len(expected.revision) == 1

    document_path = source / "test_001" / "document.json"
    document = json.loads(document_path.read_text(encoding="utf-8"))
    document["document"]["generic_name"] = "更新成分"
    document["document"]["products"][0]["brand_name"] = "更新製品"
    document_path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    units_path = source / "test_001" / "search_units.jsonl"
    with units_path.open("a", encoding="utf-8") as stream:
        stream.write(
            "\n"
            + json.dumps(
                {
                    "unit_id": "added",
                    "document_key": "test_001",
                    "section": {"code": "11.1"},
                    "text": "変更後の頭痛に注意してください",
                },
                ensure_ascii=False,
            )
        )
    changed = FileIndexSourceReader(source).read_snapshot()
    assert changed.fingerprint != initial.fingerprint
    assert len(changed.units) == 4
    assert changed.medicines[0].brand_name == "更新製品"
    seen: list[dict[str, int]] = []
    failed_drivers: list[sqlite3.Connection] = []
    rollbacks: list[Connection] = []

    def inject(connection: Connection) -> None:
        driver = connection.connection.driver_connection
        assert isinstance(driver, sqlite3.Connection)
        assert driver.in_transaction
        failed_drivers.append(driver)
        with closing(driver.cursor()) as cursor:
            counts = {
                table: cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("documents", "medicines", "units", "unit_fts")
            }
        seen.append(counts)
        if failure_phase == "normal_data":
            assert counts["documents"] == counts["medicines"] == 1
            assert counts["units"] == 0  # 新しい通常データの書込みが未完了
        elif failure_phase == "partial_fts":
            assert counts["units"] == 4
            assert counts["unit_fts"] == 1  # 4件中1件を実際に書いた状態
        else:
            assert counts["units"] == counts["unit_fts"] == 4
        raise InjectedBuildFailure(failure_phase)

    def before_sql(
        connection: Connection,
        cursor: object,
        statement: str,
        parameters: object,
        context: ExecutionContext,
        executemany: bool,
    ) -> None:
        compiled = context.compiled.statement if context.compiled is not None else None
        if (
            failure_phase == "fingerprint"
            and isinstance(compiled, Insert)
            and compiled.table is schema.index_meta
        ):
            inject(connection)
        if failure_phase == "partial_fts" and statement.lstrip().upper().startswith(
            "INSERT INTO UNIT_FTS"
        ):
            # 実driverがbatchの最初の行を書いて失敗する境界を再現する。
            # writerが渡した実SQL/paramsを使い、独立したtransactionは作らない。
            driver = connection.connection.driver_connection
            assert isinstance(driver, sqlite3.Connection)
            if executemany:
                assert isinstance(parameters, (list, tuple)) and parameters
                first_parameters = parameters[0]
            else:
                first_parameters = parameters
            assert isinstance(first_parameters, (list, tuple))
            bindings: list[str | int | float | bytes | None] = []
            for value in first_parameters:
                assert value is None or isinstance(value, (str, int, float, bytes))
                bindings.append(value)
            with closing(driver.cursor()) as partial_cursor:
                partial_cursor.execute(statement, bindings)
            inject(connection)

    def after_sql(
        connection: Connection,
        cursor: object,
        statement: str,
        parameters: object,
        context: ExecutionContext,
        executemany: bool,
    ) -> None:
        compiled = context.compiled.statement if context.compiled is not None else None
        if (
            failure_phase == "normal_data"
            and isinstance(compiled, Insert)
            and compiled.table is schema.medicines
        ):
            inject(connection)

    def observe_rollback(connection: Connection) -> None:
        rollbacks.append(connection)

    event.listen(engine, "before_cursor_execute", before_sql)
    event.listen(engine, "after_cursor_execute", after_sql)
    event.listen(engine, "rollback", observe_rollback)
    try:
        with pytest.raises(InjectedBuildFailure, match=failure_phase):
            writer.replace(changed)
    finally:
        event.remove(engine, "before_cursor_execute", before_sql)
        event.remove(engine, "after_cursor_execute", after_sql)
        event.remove(engine, "rollback", observe_rollback)
    assert len(seen) == len(rollbacks) == 1, "実際の部分書込みとrollbackの到達が必要"
    assert _snapshot_existing_database(index_path) == expected
    separate_engine = create_sqlite_engine(
        engine.url.render_as_string(hide_password=False)
    )
    try:
        with separate_engine.connect() as connection:
            assert all(
                connection.connection.driver_connection is not failed
                for failed in failed_drivers
            )
        assert _search_results(separate_engine) == before_search
    finally:
        separate_engine.dispose()
