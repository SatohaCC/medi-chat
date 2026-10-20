"""Explicit conversion from the original document to the registration contract."""

from ...domain.attachment.entities import AttachmentDocument
from ...domain.attachment.exceptions import (
    AttachmentDomainError,
    MissingOrInvalidYjError,
    MissingRevisionError,
)
from ...domain.attachment.value_objects import RegistrationVersion
from ...domain.foundation.exceptions import DomainValidationError
from ...domain.medicine.identifiers import YjCode


def registration_version(
    document: AttachmentDocument,
) -> RegistrationVersion:
    if document.source.sha256 is None:
        raise AttachmentDomainError("registration requires the original source SHA256")
    if not document.revisions:
        raise MissingRevisionError("registration requires a revision month")
    revised_at = max(
        document.revisions, key=lambda revision: revision.year_month.value
    ).year_month
    try:
        codes = frozenset(
            YjCode(product.product_code.value) for product in document.products
        )
    except DomainValidationError:
        raise MissingOrInvalidYjError("missing_or_invalid_yj") from None
    return RegistrationVersion(
        document_id=document.document_id,
        source_sha256=document.source.sha256,
        yj_codes=codes,
        revised_at=revised_at,
    )
