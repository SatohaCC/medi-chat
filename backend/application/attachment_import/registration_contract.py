"""Explicit conversion from the original document to the registration contract."""

from ...domain.attachment.entities import AttachmentDocument
from ...domain.attachment.exceptions import AttachmentDomainError
from ...domain.attachment.identifiers import ArtifactFileId
from ...domain.attachment.value_objects import RegistrationVersion
from ...domain.medicine.identifiers import YjCode


def registration_version(
    document: AttachmentDocument,
    owned_file_ids: frozenset[ArtifactFileId] = frozenset(),
) -> RegistrationVersion:
    if document.source.sha256 is None:
        raise AttachmentDomainError("registration requires the original source SHA256")
    return RegistrationVersion(
        document_id=document.document_id,
        source_sha256=document.source.sha256,
        yj_codes=frozenset(
            YjCode(product.product_code.value) for product in document.products
        ),
        owned_file_ids=owned_file_ids,
    )
