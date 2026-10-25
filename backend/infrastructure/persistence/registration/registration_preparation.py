"""Validate originals and build immutable publication inputs before locking."""

import hashlib
import json
from pathlib import PurePosixPath

from backend.application.attachment_import.errors import (
    ImportLimitExceeded,
    InvalidAttachment,
)
from backend.application.attachment_import.policies import registration_version
from backend.application.indexing.queries.services.attachment_projection import (
    project_attachment,
)
from backend.domain.attachment.exceptions import (
    MissingOrInvalidYjError,
    MissingRevisionError,
)
from backend.domain.attachment.value_objects import RegistrationVersion
from backend.infrastructure.document_import.attachment_contracts import (
    AttachmentArtifactEncoder,
)
from backend.infrastructure.persistence.mappings.attachment_document_mapping import (
    document_to_payload,
)
from backend.infrastructure.persistence.mappings.search_projection_mapping import (
    projection_records,
)
from backend.infrastructure.persistence.registration.registration_payloads import (
    PostgresRegistrationInput,
    PreparedRegistration,
)
from backend.infrastructure.serialization.search_payload_codec import (
    MAX_ARTIFACT_BYTES,
)


class RegistrationPreparer:
    def __init__(self, encoder: AttachmentArtifactEncoder):
        self.encoder = encoder

    @staticmethod
    def version(item: PostgresRegistrationInput) -> RegistrationVersion:
        try:
            version = registration_version(item.decoded.document)
        except MissingOrInvalidYjError:
            raise InvalidAttachment(
                "missing_or_invalid_yj",
                "Every listed product must have a valid YJ code",
                phase="validation",
            ) from None
        except MissingRevisionError:
            raise InvalidAttachment(
                "missing_revision",
                "A revision month is required to select the latest document",
                phase="validation",
            ) from None
        if hashlib.sha256(item.source).hexdigest() != version.source_sha256.value:
            raise InvalidAttachment(
                "source_hash_conflict",
                "Source bytes do not match the decoded document",
                phase="validation",
            )
        return version

    def prepare(self, item: PostgresRegistrationInput) -> PreparedRegistration:
        version = self.version(item)
        for figure in item.figures:
            name = PurePosixPath(figure.logical_name)
            if (
                name.is_absolute()
                or ".." in name.parts
                or "\\" in figure.logical_name
                or ":" in figure.logical_name
                or not figure.logical_name
                or not figure.media_type
            ):
                raise InvalidAttachment(
                    "unsafe_figure", "Figure name is unsafe", phase="validation"
                )
        projected = project_attachment(item.decoded.document)
        bundle = self.encoder.encode(
            item.decoded.document, projected, item.decoded.source_info
        )
        if (
            sum(
                len(file.content)
                for file in bundle.files
                if file.name != "source_metadata.json"
            )
            > MAX_ARTIFACT_BYTES
        ):
            raise ImportLimitExceeded(
                "artifact_size_limit", "Generated artifacts exceed the size limit"
            )
        artifacts = {file.name: file.content for file in bundle.files}
        metadata = json.loads(artifacts["document.json"])
        units, products = projection_records(item.decoded.document)
        return PreparedRegistration(
            version,
            {
                "structure": document_to_payload(item.decoded.document),
                "catalogue": {
                    "document": metadata["document"],
                    "source": {
                        "pmda_url": metadata["source"]["pmda_url"],
                        "sha256": version.source_sha256.value,
                    },
                },
                "unit_products": products,
                "source": item.source,
                "filename": metadata["source"]["file"],
                "validation": json.loads(artifacts["validation.json"]),
                "figures": item.figures,
                "units": units,
                "result": bundle.result,
            },
        )
