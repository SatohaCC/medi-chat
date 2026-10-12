"""複製した旧索引のschemaを検証する境界。"""

import re
import sqlite3
from contextlib import closing
from pathlib import Path

from sqlalchemy.dialects.sqlite import dialect

from .schema import metadata

_LEGACY_TABLES = ("documents", "medicines", "units", "index_meta")


def _quoted(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _validate_table(connection: sqlite3.Connection, name: str) -> None:
    table = metadata.tables[name]
    columns = connection.execute(f"PRAGMA table_xinfo({_quoted(name)})").fetchall()
    expected_pk = [column.name for column in table.primary_key.columns]
    actual_pk = [row[1] for row in sorted(columns, key=lambda row: row[5]) if row[5]]
    if actual_pk != expected_pk:
        raise ValueError(f"Primary key mismatch in {name}")
    expected = [
        (
            column.name,
            str(column.type.compile(dialect=dialect())).upper(),
            int(not column.nullable),
            None,
            0,
        )
        for column in table.columns
    ]
    actual = [(row[1], row[2].upper(), row[3], row[4], row[6]) for row in columns]
    if actual != expected:
        raise ValueError(f"Column definition mismatch in {name}")
    sql = connection.execute(
        "SELECT sql FROM sqlite_schema WHERE type='table' AND name=?", (name,)
    ).fetchone()[0]
    if re.search(
        r"\b(CHECK|REFERENCES|UNIQUE|COLLATE|WITHOUT|STRICT|CONFLICT|ASC|DESC)\b",
        sql,
        re.I,
    ):
        raise ValueError(f"Unexpected table constraints in {name}")
    indexes = connection.execute(f"PRAGMA index_list({_quoted(name)})").fetchall()
    primary_indexes = [row for row in indexes if row[3] == "pk"]
    if len(primary_indexes) != int(bool(expected_pk)):
        raise ValueError(f"Primary key index mismatch in {name}")
    for primary_index in primary_indexes:
        keys = connection.execute(
            f"PRAGMA index_xinfo({_quoted(primary_index[1])})"
        ).fetchall()
        if [(row[2], row[3], row[4]) for row in keys if row[5]] != [
            (column, 0, "BINARY") for column in expected_pk
        ]:
            raise ValueError(f"Primary key sort or collation mismatch in {name}")
    expected_indexes = {
        index.name: index for index in table.indexes if index.name is not None
    }
    actual_indexes = {row[1]: row for row in indexes if row[3] != "pk"}
    if actual_indexes.keys() != expected_indexes.keys():
        raise ValueError(f"Index definitions mismatch in {name}")
    for index_name, index in expected_indexes.items():
        row = actual_indexes[index_name]
        definition = connection.execute(
            f"PRAGMA index_xinfo({_quoted(index_name)})"
        ).fetchall()
        keys = [(item[2], item[3], item[4]) for item in definition if item[5]]
        if (
            row[2]
            or row[4]
            or keys != [(column.name, 0, "BINARY") for column in index.columns]
        ):
            raise ValueError(f"Index definition mismatch: {index_name}")


def _validate_schema(connection: sqlite3.Connection) -> None:
    objects = connection.execute("SELECT type, name, sql FROM sqlite_schema").fetchall()
    ordinary_tables = set(_LEGACY_TABLES)
    fts_tables = {
        "unit_fts",
        *(
            f"unit_fts_{suffix}"
            for suffix in ("data", "idx", "content", "docsize", "config")
        ),
    }
    actual_tables = {name for kind, name, _ in objects if kind == "table"}
    if actual_tables != ordinary_tables | fts_tables:
        raise ValueError("Legacy table schema mismatch or unknown objects")
    expected_indexes = {
        index.name for name in _LEGACY_TABLES for index in metadata.tables[name].indexes
    } | {f"sqlite_autoindex_{name}_1" for name in ("documents", "units", "index_meta")}
    if any(
        kind not in ("table", "index")
        or (kind == "index" and name not in expected_indexes)
        for kind, name, _ in objects
    ):
        raise ValueError("Unknown schema objects or index definitions")
    for name in _LEGACY_TABLES:
        _validate_table(connection, name)
    version = connection.execute(
        "SELECT value FROM index_meta WHERE key='schema_version'"
    ).fetchall()
    if version != [("3",)]:
        raise ValueError("Legacy schema_version must be 3")
    fts_sql = next(sql for kind, name, sql in objects if name == "unit_fts")
    # tokenizerの値の引用と、識別子の引用を別々に正規化する。
    canonical = re.sub(r"(tokenize\s*=\s*)\"([^\"]*)\"", r"\1'\2'", fts_sql.lower())
    canonical = re.sub(r"[\s\"`\[\]]", "", canonical).replace("ifnotexists", "")
    expected_fts = (
        "createvirtualtableunit_ftsusingfts5(unit_idunindexed,"
        "document_keyunindexed,section_codeunindexed,kindunindexed,"
        "query_text,drug_name,tokenize='trigram')"
    )
    if canonical != expected_fts:
        raise ValueError("FTS definition mismatch: expected v3 trigram columns")


def validate_legacy_schema(index_path: Path) -> None:
    with closing(
        sqlite3.connect(f"{index_path.resolve().as_uri()}?mode=ro", uri=True)
    ) as connection:
        _validate_schema(connection)
