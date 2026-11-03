"""Data structures for package_insert source information, decoded package_inserts, and artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.application.package_insert_import.commands.models import ImportResult
from backend.domain.package_insert.entities import PackageInsertDocument
from backend.domain.package_insert.identifiers import DocumentId


@dataclass(frozen=True, slots=True)
class PackageInsertSourceInformation:
    """原本のメタデータ・構造化行・検証結果・変換イベントを渡す境界情報。"""

    document: dict[str, Any]
    rows: list[dict[str, Any]]
    validation: dict[str, Any]
    events: list[dict[str, object]]


@dataclass(frozen=True, slots=True)
class DecodedPackageInsert:
    document: PackageInsertDocument
    source_info: PackageInsertSourceInformation


@dataclass(frozen=True, slots=True)
class ArtifactFile:
    name: str
    content: bytes


@dataclass(frozen=True, slots=True)
class ArtifactBundle:
    document_id: DocumentId
    source_sha256: str
    files: tuple[ArtifactFile, ...]
    result: ImportResult
