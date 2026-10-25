"""Non-SQL adapter that coordinates attachment decoding and registration publishing."""

from __future__ import annotations

from collections.abc import Callable

from backend.application.attachment_import.commands.models import ImportResult
from backend.infrastructure.document_import.attachment_contracts import (
    AttachmentDecoder,
    AttachmentRegistrationPublisher,
)


class OriginalDocumentRegistration:
    def __init__(
        self, *, decoder: AttachmentDecoder, publisher: AttachmentRegistrationPublisher
    ):
        self.decoder = decoder
        self.publisher = publisher

    def register(
        self, source: bytes, *, original_filename: str, check_cancel: Callable[[], None]
    ) -> ImportResult:
        check_cancel()
        decoded = self.decoder.decode(source, original_filename=original_filename)
        check_cancel()
        return self.publisher.publish(decoded, source, check_cancel=check_cancel)
