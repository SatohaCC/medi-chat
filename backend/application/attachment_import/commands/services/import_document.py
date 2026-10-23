from collections.abc import Callable

from backend.application.attachment_import.commands.models import ImportResult
from backend.application.attachment_import.interfaces.original_document_registration import (
    OriginalDocumentRegistration,
)


def import_document(
    source: bytes,
    *,
    original_filename: str,
    registration: OriginalDocumentRegistration,
    check_cancel: Callable[[], None],
) -> ImportResult:
    check_cancel()
    return registration.register(
        source, original_filename=original_filename, check_cancel=check_cancel
    )
