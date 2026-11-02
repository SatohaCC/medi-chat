"""Protocols for package_insert decoding, artifact encoding, and registration publishing."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from backend.application.indexing.queries.models import SearchUnit
from backend.application.package_insert_import.commands.models import ImportResult
from backend.domain.package_insert.entities import PackageInsertDocument
from backend.infrastructure.document_import.package_insert_payloads import (
    ArtifactBundle,
    DecodedPackageInsert,
    PackageInsertSourceInformation,
)


class PackageInsertDecoder(Protocol):
    def decode(
        self, source: bytes, *, original_filename: str
    ) -> DecodedPackageInsert: ...


class PackageInsertArtifactEncoder(Protocol):
    def encode(
        self,
        document: PackageInsertDocument,
        search_units: tuple[SearchUnit, ...],
        source_info: PackageInsertSourceInformation,
    ) -> ArtifactBundle: ...


class PackageInsertRegistrationPublisher(Protocol):
    def publish(
        self,
        decoded: DecodedPackageInsert,
        source: bytes,
        *,
        check_cancel: Callable[[], None],
    ) -> ImportResult: ...
