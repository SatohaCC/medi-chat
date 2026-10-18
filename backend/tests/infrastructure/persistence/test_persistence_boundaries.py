"""通常Core操作の境界。実startup/build/importは最終配線後に再検証する。"""

from __future__ import annotations

import ast
import asyncio
import json
import re
from pathlib import Path

import pytest
from backend.application.indexing.index_models import (
    IndexBuildResult,
    IndexDocument,
    IndexUnit,
    SourceSnapshot,
)
from backend.application.medicine.product_models import RegisteredMedicine
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.attachment.primitives import PmdaUrl
from backend.domain.attachment.value_objects import (
    AttachmentProductRevision,
    MedicineDocumentReference,
)
from backend.domain.medicine.entities import MedicineProduct
from backend.domain.medicine.identifiers import YjCode
from backend.infrastructure.persistence import schema
from backend.infrastructure.persistence.index_writer import SqlAlchemyIndexWriter
from backend.infrastructure.persistence.medicine_reader import SqlAlchemyMedicineReader
from backend.tests.infrastructure.persistence.test_alembic_migrations import (
    _migrate_database,
)
from backend.tests.support.paths import BACKEND_ROOT
from sqlalchemy import create_engine, event, insert, select, text
from sqlalchemy.engine import URL, Connection, ExecutionContext
from sqlalchemy.sql import visitors
from sqlalchemy.sql.dml import Delete, Insert, Update
from sqlalchemy.sql.elements import ClauseElement
from sqlalchemy.sql.schema import Table
from sqlalchemy.sql.selectable import Select


@pytest.fixture
def source_snapshot() -> SourceSnapshot:
    medicine = RegisteredMedicine(
        medicine=MedicineProduct(
            yj_code=YjCode("1234567A0000"),
            brand_name="テスト薬",
            generic_name="テスト成分",
            english_name="TestDrug",
            hiragana_name="てすとやく",
        ),
        reference=MedicineDocumentReference(
            document_id=DocumentId("test_001"),
            pmda_url=PmdaUrl("https://example.test/package-insert"),
            revision=AttachmentProductRevision(
                {"date": "2026-10-03", "source": {"note": "原文"}}
            ),
        ),
    )
    return SourceSnapshot(
        documents=(
            IndexDocument(
                "test_001",
                {
                    "document": {
                        "company_identifier": "test",
                        "package_insert_no": "001",
                        "generic_name": "テスト成分",
                        "products": [
                            {"yj_code": "1234567A0000", "brand_name": "テスト薬"}
                        ],
                    },
                    "source": {"pmda_url": "https://example.test/package-insert"},
                },
            ),
        ),
        medicines=(medicine,),
        units=(
            IndexUnit(
                unit_id="test_001:000",
                document_id="test_001",
                section_code="11.1",
                kind="text",
                payload={
                    "unit_id": "test_001:000",
                    "document_key": "test_001",
                    "section": {"code": "11.1", "title": "重大な副作用"},
                    "kind": "text",
                    "text": "アスピリンに注意してください",
                    "columns": {"drug_name": "アスピリン"},
                },
                query_text="アスピリンに注意してください",
                drug_name="アスピリン",
            ),
        ),
        fingerprint="tc25-source",
    )


def _private_memory_fts_ddl(tree: ast.AST) -> set[ast.Call]:
    allowed: set[ast.Call] = set()
    for scope in ast.walk(tree):
        if not isinstance(scope, ast.With):
            continue
        for item in scope.items:
            if not isinstance(item.optional_vars, ast.Name):
                continue
            binding = item.optional_vars.id
            context = item.context_expr
            if not (
                isinstance(context, ast.Call)
                and isinstance(context.func, ast.Name)
                and context.func.id == "closing"
                and len(context.args) == 1
            ):
                continue
            connection = context.args[0]
            if not (
                isinstance(connection, ast.Call)
                and isinstance(connection.func, ast.Attribute)
                and isinstance(connection.func.value, ast.Name)
                and connection.func.value.id == "sqlite3"
                and connection.func.attr == "connect"
                and connection.args
                and isinstance(connection.args[0], ast.Constant)
                and connection.args[0].value == ":memory:"
            ):
                continue
            body = ast.Module(body=scope.body, type_ignores=[])
            if any(
                isinstance(n, ast.Name)
                and n.id == binding
                and isinstance(n.ctx, ast.Store)
                for n in ast.walk(body)
            ):
                continue
            for call in ast.walk(body):
                if not isinstance(call, ast.Call) or not isinstance(
                    call.func, ast.Attribute
                ):
                    continue
                if not (
                    isinstance(call.func.value, ast.Name)
                    and call.func.value.id == binding
                    and call.func.attr == "execute"
                    and call.args
                    and isinstance(call.args[0], ast.Constant)
                ):
                    continue
                if re.match(
                    r"\s*CREATE VIRTUAL TABLE \w+ USING fts5\(",
                    str(call.args[0].value),
                    re.I,
                ):
                    allowed.add(call)
    # Cached private connections outlive a single search. Check every helper
    # call against the local :memory: allocation instead of requiring `with`.
    for owner in ast.walk(tree):
        if not isinstance(owner, ast.ClassDef):
            continue
        helpers = {n.name: n for n in owner.body if isinstance(n, ast.FunctionDef)}
        for name, helper in helpers.items():
            if name != "_build_fts":
                continue
            calls = []
            safe = True
            for method in helpers.values():
                for call in ast.walk(method):
                    if not (
                        isinstance(call, ast.Call)
                        and isinstance(call.func, ast.Attribute)
                        and isinstance(call.func.value, ast.Name)
                        and call.func.value.id == "self"
                        and call.func.attr == name
                    ):
                        continue
                    calls.append(call)
                    if not call.args or not isinstance(call.args[0], ast.Name):
                        safe = False
                        continue
                    binding = call.args[0].id
                    assignments = [
                        n
                        for n in ast.walk(method)
                        if isinstance(n, ast.Assign)
                        and n.lineno < call.lineno
                        and any(
                            isinstance(t, ast.Name) and t.id == binding
                            for t in n.targets
                        )
                    ]
                    allocation = (
                        max(assignments, key=lambda n: n.lineno).value
                        if assignments
                        else None
                    )
                    safe &= bool(
                        isinstance(allocation, ast.Call)
                        and isinstance(allocation.func, ast.Attribute)
                        and isinstance(allocation.func.value, ast.Name)
                        and allocation.func.value.id == "sqlite3"
                        and allocation.func.attr == "connect"
                        and allocation.args
                        and isinstance(allocation.args[0], ast.Constant)
                        and allocation.args[0].value == ":memory:"
                    )
            if calls and safe:
                allowed.update(
                    n
                    for n in ast.walk(helper)
                    if isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Attribute)
                    and isinstance(n.func.value, ast.Name)
                    and n.func.value.id == "connection"
                    and n.func.attr == "execute"
                    and n.args
                    and isinstance(n.args[0], ast.Constant)
                    and re.match(
                        r"\s*CREATE VIRTUAL TABLE \w+ USING fts5\(",
                        str(n.args[0].value),
                        re.I,
                    )
                )
    return allowed


def _assert_new_persistence_sources() -> None:
    backend_dir = BACKEND_ROOT
    persistence_dir = backend_dir / "infrastructure" / "persistence"
    paths = [
        *persistence_dir.rglob("*.py"),
        *(backend_dir / "domain").rglob("*.py"),
        *(backend_dir / "application").rglob("*.py"),
    ]
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        private_ddl = _private_memory_fts_ddl(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = (
                node.func.attr
                if isinstance(node.func, ast.Attribute)
                else node.func.id
                if isinstance(node.func, ast.Name)
                else ""
            )
            assert name not in {
                "create_all",
                "stamp",
                "CreateTable",
                "DropTable",
                "CreateIndex",
                "DropIndex",
            }, f"{path}:{node.lineno}: DDLを通常処理から実行する"
            if not node.args or not isinstance(node.args[0], ast.Constant):
                continue
            value = node.args[0].value
            if not isinstance(value, str):
                continue
            if re.search(r"\b(?:unit_fts|fts5|bm25)\b", value, re.I):
                assert path.is_relative_to(persistence_dir), (
                    f"{path}:{node.lineno}: FTS SQLが外側へ漏れる"
                )
            if name in {"text", "execute", "exec_driver_sql"}:
                assert (
                    not re.match(r"\s*(?:create|alter|drop)\b", value, re.I)
                    or node in private_ddl
                    and path.is_relative_to(persistence_dir)
                ), f"{path}:{node.lineno}: 通常処理にDDL SQLがある"


def test_private_fts_ddl_exemption_requires_memory_connection(monkeypatch):
    path = BACKEND_ROOT / "infrastructure/persistence/generation_runtime.py"
    content = path.read_text(encoding="utf-8")
    assert len(_private_memory_fts_ddl(ast.parse(content))) == 1
    persisted = ast.parse(
        content.replace('sqlite3.connect(":memory:"', 'sqlite3.connect("index.sqlite3"')
    )
    assert _private_memory_fts_ddl(persisted) == set()
    assert any(
        isinstance(n, ast.Constant)
        and isinstance(n.value, str)
        and n.value.startswith("CREATE VIRTUAL TABLE")
        for n in ast.walk(persisted)
    )
    original_read = Path.read_text

    def read_with_persisted_connection(self, *args, **kwargs):
        value = original_read(self, *args, **kwargs)
        return (
            value.replace(
                'sqlite3.connect(":memory:"', 'sqlite3.connect("index.sqlite3"'
            )
            if self == path
            else value
        )

    monkeypatch.setattr(Path, "read_text", read_with_persisted_connection)
    with pytest.raises(AssertionError, match="通常処理にDDL SQLがある"):
        _assert_new_persistence_sources()


def _select_uses_table(statement: Select, table: Table) -> bool:
    # select(Table)・select(Table.c.column)・JOIN/aliasのいずれも、実FROMのTableで観測する。
    return any(
        node is table
        for from_clause in statement.get_final_froms()
        for node in visitors.iterate(from_clause)
    )


@pytest.mark.parametrize("operation", ["reader", "writer"])
def test_core_owns_data_access_and_alembic_owns_ddl(
    tmp_path: Path,
    operation: str,
    source_snapshot: SourceSnapshot,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in (
        "MEDI_CHAT_STRUCTURED_DIR",
        "MEDI_CHAT_INDEX_PATH",
        "MEDI_CHAT_DATABASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)
    source_dir = tmp_path / "structured"
    source_dir.mkdir()
    index_path = tmp_path / "core.sqlite3"
    # migrationだけにDDLを許可し、準備完了後に通常操作のSQL観測を開始する。
    _migrate_database(index_path, source_dir)
    engine = create_engine(URL.create("sqlite", database=index_path.as_posix()))
    statements: list[tuple[Connection, str, ClauseElement | None]] = []
    transactions: list[str] = []

    def record_sql(
        connection: Connection,
        cursor: object,
        statement: str,
        parameters: object,
        context: ExecutionContext,
        executemany: bool,
    ) -> None:
        compiled = context.compiled
        statements.append(
            (
                connection,
                statement,
                compiled.statement if compiled is not None else None,
            )
        )

    def record_begin(connection: Connection) -> None:
        transactions.append("begin")

    def record_commit(connection: Connection) -> None:
        transactions.append("commit")

    def record_rollback(connection: Connection) -> None:
        transactions.append("rollback")

    listeners = {
        "before_cursor_execute": record_sql,
        "begin": record_begin,
        "commit": record_commit,
        "rollback": record_rollback,
    }
    try:
        if operation == "reader":
            medicine = source_snapshot.medicines[0]
            seed = {
                "document_key": medicine.document_id.value,
                "yj_code": medicine.yj_code.value
                if medicine.yj_code is not None
                else None,
                "brand_name": medicine.brand_name,
                "generic_name": medicine.generic_name,
                "english_name": medicine.english_name,
                "hiragana_name": medicine.hiragana_name,
                "pmda_url": medicine.pmda_url.value,
            }
            seed["revision"] = source_snapshot.medicines[0].revision.to_dict()
            seed["revision_json"] = json.dumps(seed.pop("revision"), ensure_ascii=False)
            with engine.begin() as connection:
                connection.execute(insert(schema.medicines), seed)
        for name, listener in listeners.items():
            event.listen(engine, name, listener)
        try:
            if operation == "reader":
                medicines = asyncio.run(
                    SqlAlchemyMedicineReader(engine).read_medicines()
                )
                assert medicines == source_snapshot.medicines
                assert type(medicines) is tuple
                assert all(
                    type(medicine) is RegisteredMedicine for medicine in medicines
                )
            else:
                result = SqlAlchemyIndexWriter(engine).replace(source_snapshot)
                assert type(result) is IndexBuildResult
                assert result == IndexBuildResult(document_count=1, unit_count=1)
        finally:
            for name, listener in listeners.items():
                event.remove(engine, name, listener)

        assert statements, "注入したEngine上のSQLAlchemy操作を観測できない"
        assert transactions[0] == "begin"
        assert (
            ("commit" in transactions)
            if operation == "writer"
            else ("commit" in transactions or "rollback" in transactions)
        )
        assert all(connection.closed for connection, _, _ in statements)
        normal_tables = (
            schema.documents,
            schema.medicines,
            schema.units,
            schema.index_meta,
        )
        core_statements: list[ClauseElement] = []
        for _, sql, compiled in statements:
            normalized_sql = sql.replace('"', "").lower()
            assert not re.match(
                r"\s*(?:create|alter|drop|vacuum|reindex)\b", normalized_sql
            )
            assert not re.search(
                r"\b(?:insert|update|delete)\b.*\balembic_version\b",
                normalized_sql,
                re.S,
            )
            if any(
                re.search(
                    rf"\b(?:from|join|into|update)\s+{table.name}\b", normalized_sql
                )
                for table in normal_tables
            ):
                assert isinstance(compiled, (Select, Insert, Update, Delete)), sql
                core_statements.append(compiled)
        assert core_statements
        if operation == "reader":
            assert any(
                isinstance(statement, Select)
                and _select_uses_table(statement, schema.medicines)
                for statement in core_statements
            )
        else:
            for table in normal_tables:
                assert isinstance(table, Table)
                assert any(
                    isinstance(statement, Insert) and statement.table is table
                    for statement in core_statements
                ), table.name
            with engine.connect() as connection:
                assert connection.execute(
                    select(schema.documents.c.document_key)
                ).all() == [("test_001",)]
                assert connection.execute(
                    select(schema.medicines.c.brand_name)
                ).all() == [("テスト薬",)]
                assert connection.execute(select(schema.units.c.unit_id)).all() == [
                    ("test_001:000",)
                ]
                assert connection.execute(
                    select(schema.index_meta.c.value).where(
                        schema.index_meta.c.key == "source_fingerprint"
                    )
                ).all() == [("tc25-source",)]
                assert connection.execute(
                    text("SELECT unit_id FROM unit_fts WHERE unit_fts MATCH :query"),
                    {"query": "スピリ"},
                ).all() == [("test_001:000",)]
        _assert_new_persistence_sources()
    finally:
        engine.dispose()
