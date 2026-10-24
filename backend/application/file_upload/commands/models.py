"""Bounded, immutable original-file upload metadata."""

from dataclasses import dataclass

from backend.domain.attachment.primitives import AttachmentSha256
from backend.domain.foundation.exceptions import DomainValidationError

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

    def part_size(self, index: int, *, chunk_bytes: int) -> int:
        if chunk_bytes <= 0 or index < 0 or index * chunk_bytes >= self.byte_size:
            raise ValueError("Invalid upload part index")
        return min(chunk_bytes, self.byte_size - index * chunk_bytes)


@dataclass(frozen=True, slots=True)
class UploadedSource:
    spec: UploadSpec
    source: bytes
