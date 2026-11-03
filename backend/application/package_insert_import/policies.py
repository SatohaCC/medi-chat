"""Explicit conversion from the original document to the registration contract."""

from backend.domain.foundation.exceptions import DomainValidationError
from backend.domain.medicine.identifiers import YjCode
from backend.domain.package_insert.entities import PackageInsertDocument
from backend.domain.package_insert.exceptions import (
    MissingOrInvalidYjError,
    MissingRevisionError,
    PackageInsertDomainError,
)
from backend.domain.package_insert.value_objects import RegistrationVersion


def registration_version(
    document: PackageInsertDocument,
) -> RegistrationVersion:
    if document.source.sha256 is None:
        raise PackageInsertDomainError(
            "registration requires the original source SHA256"
        )
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
