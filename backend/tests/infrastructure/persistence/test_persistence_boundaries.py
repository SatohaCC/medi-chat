"""PG-003/040: production storage has no SQLite or implicit schema DDL."""

import ast
import re
from pathlib import Path

import pytest
from backend.tests.support.paths import BACKEND_ROOT


def assert_runtime_storage_boundaries():
    for directory in (
        "domain",
        "application",
        "infrastructure/persistence",
        "infrastructure/composition",
    ):
        for path in (BACKEND_ROOT / directory).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = (
                        [node.module or ""]
                        if isinstance(node, ast.ImportFrom)
                        else [alias.name for alias in node.names]
                    )
                    assert not any(
                        name == "sqlite3" or name.startswith("sqlite3.")
                        for name in names
                    ), f"{path}:{node.lineno}: runtime SQLite is forbidden"
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
                }, f"{path}:{node.lineno}: implicit DDL is forbidden"
                if (
                    name in {"text", "execute", "exec_driver_sql"}
                    and node.args
                    and isinstance(node.args[0], ast.Constant)
                ):
                    value = node.args[0].value
                    if isinstance(value, str):
                        assert not re.match(
                            r"\s*(?:create|alter|drop)\b", value, re.I
                        ), f"{path}:{node.lineno}: runtime SQL DDL is forbidden"


def test_postgres_runtime_has_no_sqlite_or_implicit_ddl():
    assert_runtime_storage_boundaries()


@pytest.mark.parametrize(
    "injection",
    [
        "import sqlite3\nconnection = sqlite3.connect(':memory:')\n",
        "metadata.create_all(engine)\n",
        "connection.execute('CREATE TABLE unsafe (id int)')\n",
    ],
)
def test_runtime_storage_guard_rejects_sqlite_and_ddl_injections(
    monkeypatch, injection
):
    target = BACKEND_ROOT / "infrastructure/persistence/postgres_runtime.py"
    original = Path.read_text

    def read(path, *args, **kwargs):
        result = original(path, *args, **kwargs)
        return result + "\n" + injection if path == target else result

    monkeypatch.setattr(Path, "read_text", read)
    with pytest.raises(AssertionError, match="(?:SQLite|DDL).*forbidden"):
        assert_runtime_storage_boundaries()
