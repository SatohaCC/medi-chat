"""Protocols for attachment decoding, artifact encoding, and registration publishing."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from backend.application.attachment_import.commands.models import ImportResult
from backend.application.indexing.queries.models import SearchUnit
from backend.domain.attachment.entities import AttachmentDocument
from backend.infrastructure.document_import.attachment_payloads import (
    ArtifactBundle,
    AttachmentSourceInformation,
    DecodedAttachment,
)


class AttachmentDecoder(Protocol):
    def decode(self, source: bytes, *, original_filename: str) -> DecodedAttachment: ...


class AttachmentArtifactEncoder(Protocol):
    def encode(
        self,
        document: AttachmentDocument,
        search_units: tuple[SearchUnit, ...],
        source_info: AttachmentSourceInformation,
    ) -> ArtifactBundle: ...


class AttachmentRegistrationPublisher(Protocol):
    def publish(
        self,
        decoded: DecodedAttachment,
        source: bytes,
        *,
        check_cancel: Callable[[], None],
    ) -> ImportResult: ...
