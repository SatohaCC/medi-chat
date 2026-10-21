"""Bounded, immutable original-file upload metadata."""

from dataclasses import dataclass

from ...domain.attachment.primitives import AttachmentSha256
from ...domain.foundation.exceptions import DomainValidationError

CHUNK_BYTES = 3 * 1024 * 1024
MAX_SOURCE_BYTES = 10 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class UploadSpec:
    filename: str
    byte_size: int
    source_sha256: str

    def __post_init__(self) -> None:
        if not 1 <= self.byte_size <= MAX_SOURCE_BYTES:
            raise ValueError("XML must contain between 1 byte and 10 MiB")
        try:
            digest = AttachmentSha256(self.source_sha256)
        except DomainValidationError:
            raise ValueError("Invalid source SHA-256") from None
        object.__setattr__(self, "source_sha256", digest.value)
        if not self.filename or len(self.filename) > 255:
            raise ValueError("Invalid filename")

    def part_size(self, index: int) -> int:
        if index < 0 or index * CHUNK_BYTES >= self.byte_size:
            raise ValueError("Invalid upload part index")
        return min(CHUNK_BYTES, self.byte_size - index * CHUNK_BYTES)


@dataclass(frozen=True, slots=True)
class UploadedSource:
    spec: UploadSpec
    source: bytes | None
    document_id: str | None
