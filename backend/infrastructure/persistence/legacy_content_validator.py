"""複製した旧索引の内容整合性を検証する境界。"""

import json
import sqlite3
from collections import Counter
from pathlib import Path

from sqlalchemy import Text, column, select, table
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DatabaseError

from ...application.indexing.index_models import IndexUnit
from ...domain.json_types import JsonValue
from ..index_payloads import build_index_document, build_index_unit
from ..json_payloads import parse_json_object
from . import schema
from .readonly_engine import create_readonly_engine

_FTS = table(
    "unit_fts",
    *(
        column(name, Text)
        for name in (
            "unit_id",
            "document_key",
            "section_code",
            "kind",
            "query_text",
            "drug_name",
        )
    ),
)


def _json_object(value: str, location: str) -> dict[str, JsonValue]:
    try:
        return parse_json_object(value)
    except (ValueError, TypeError) as error:
        raise ValueError(f"Invalid JSON object in {location}") from error


def _read_document_products(
    connection: Connection,
) -> tuple[set[str], list[tuple[str | None, ...]]]:
    documents: set[str] = set()
    expected_medicines: list[tuple[str | None, ...]] = []
    for row in connection.execute(select(schema.documents)).mappings():
        payload = _json_object(row["payload_json"], "documents")
        try:
            document, medicines = build_index_document(payload)
        except (TypeError, ValueError, KeyError) as error:
            raise ValueError("Invalid document JSON structure") from error
        if document.document_id != row["document_key"]:
            raise ValueError("Document key does not match JSON metadata")
        documents.add(row["document_key"])
        expected_medicines.extend(
            (
                medicine.document_id.value,
                medicine.yj_code.value if medicine.yj_code is not None else None,
                medicine.brand_name,
                medicine.generic_name,
                medicine.english_name,
                medicine.hiragana_name,
                medicine.pmda_url.value,
                json.dumps(medicine.revision.to_dict(), sort_keys=True),
            )
            for medicine in medicines
        )
    return documents, expected_medicines


def _validate_medicines(
    connection: Connection,
    documents: set[str],
    expected_medicines: list[tuple[str | None, ...]],
) -> None:
    actual_medicines: list[tuple[str | None, ...]] = []
    for row in connection.execute(select(schema.medicines)).mappings():
        revision = _json_object(row["revision_json"], "medicines revision")
        if row["document_key"] not in documents:
            raise ValueError("Medicine references a missing document")
        actual_medicines.append(
            tuple(
                row[column.name]
                for column in schema.medicines.columns
                if column.name != "revision_json"
            )
            + (json.dumps(revision, sort_keys=True),)
        )
    if Counter(actual_medicines) != Counter(expected_medicines):
        raise ValueError("Medicines differ from document products or revisions")


def _read_units(connection: Connection, documents: set[str]) -> dict[str, IndexUnit]:
    units: dict[str, IndexUnit] = {}
    for row in connection.execute(select(schema.units)).mappings():
        payload = _json_object(row["payload_json"], "units")
        if row["document_key"] not in documents:
            raise ValueError("Unit references a missing document")
        if payload.get("document_key") != row["document_key"]:
            raise ValueError("Unit document reference differs from JSON")
        try:
            unit = build_index_unit(payload, row["document_key"])
        except (TypeError, ValueError, KeyError) as error:
            raise ValueError("Invalid unit JSON structure") from error
        if (unit.unit_id, unit.section_code, unit.kind) != (
            row["unit_id"],
            row["section_code"],
            row["kind"],
        ):
            raise ValueError("Unit columns differ from JSON")
        units[unit.unit_id] = unit
    return units


def _validate_fts(connection: Connection, units: dict[str, IndexUnit]) -> None:
    seen: set[str] = set()
    for row in connection.execute(select(_FTS)).mappings():
        identifier = row["unit_id"]
        if identifier not in units or identifier in seen:
            raise ValueError("FTS-unit correspondence is not one-to-one")
        unit = units[identifier]
        if tuple(
            row[name]
            for name in (
                "document_key",
                "section_code",
                "kind",
                "query_text",
                "drug_name",
            )
        ) != (
            unit.document_id,
            unit.section_code,
            unit.kind,
            unit.query_text,
            unit.drug_name,
        ):
            raise ValueError("FTS values differ from unit content")
        seen.add(identifier)
    if seen != units.keys():
        raise ValueError("FTS entries are missing for units")


def _validate_content(connection: Connection) -> None:
    if connection.exec_driver_sql("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise ValueError("SQLite integrity check failed")
    documents, expected_medicines = _read_document_products(connection)
    _validate_medicines(connection, documents, expected_medicines)
    units = _read_units(connection, documents)
    _validate_fts(connection, units)


def validate_legacy_content(index_path: Path) -> None:
    engine = create_readonly_engine(index_path)
    try:
        with engine.connect() as connection:
            _validate_content(connection)
    except (sqlite3.DatabaseError, DatabaseError) as error:
        raise ValueError("SQLite integrity validation failed: corrupt index") from error
    finally:
        engine.dispose()
