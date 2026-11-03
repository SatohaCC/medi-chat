"""Typed preparation inputs and payloads for PostgreSQL publication."""

from dataclasses import dataclass
from typing import Any, TypedDict

from backend.application.package_insert_import.commands.models import ImportResult
from backend.domain.foundation.json_types import JsonValue
from backend.domain.package_insert.value_objects import RegistrationVersion
from backend.infrastructure.document_import.package_insert_payloads import (
    DecodedPackageInsert,
)


@dataclass(frozen=True)
class FigureInput:
    logical_name: str
    media_type: str
    content: bytes


@dataclass(frozen=True)
class PostgresRegistrationInput:
    decoded: DecodedPackageInsert
    source: bytes
    figures: tuple[FigureInput, ...] = ()


class NewVersionPayload(TypedDict):
    structure: dict[str, Any]
    catalogue: dict[str, Any]
    source: bytes
    filename: str
    validation: dict[str, Any]
    figures: tuple[FigureInput, ...]
    units: list[dict[str, JsonValue]]
    unit_products: list[dict[str, str]]
    result: ImportResult


@dataclass(frozen=True)
class PreparedRegistration:
    version: RegistrationVersion
    payload: NewVersionPayload | None
