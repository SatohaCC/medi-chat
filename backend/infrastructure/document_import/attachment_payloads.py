"""Data structures for attachment source information, decoded attachments, and artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.application.attachment_import.commands.models import ImportResult
from backend.domain.attachment.entities import AttachmentDocument
from backend.domain.attachment.identifiers import DocumentId


@dataclass(frozen=True, slots=True)
class AttachmentSourceInformation:
    """原本のメタデータ・構造化行・検証結果・変換イベントを渡す境界情報。"""

    document: dict[str, Any]
    rows: list[dict[str, Any]]
    validation: dict[str, Any]
    events: list[dict[str, object]]


@dataclass(frozen=True, slots=True)
class DecodedAttachment:
    document: AttachmentDocument
    source_info: AttachmentSourceInformation


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
