"""Canonical version-complete stored projection shared by publish and rebuild."""

import json

from backend.application.attachment_import.policies import registration_version
from backend.application.indexing.queries.services.attachment_projection import (
    project_active_attachment,
)
from backend.domain.attachment.entities import AttachmentDocument
from backend.domain.foundation.json_types import JsonValue
from backend.infrastructure.serialization.search_payload_codec import (
    build_index_unit,
    encode_registered_units,
)


def projection_records(
    document: AttachmentDocument,
) -> tuple[list[dict[str, JsonValue]], list[dict[str, str]]]:
    version = registration_version(document)
    units: list[dict[str, JsonValue]] = []
    for position, line in enumerate(
        encode_registered_units(
            document, project_active_attachment(document, version.yj_codes)
        ).splitlines()
    ):
        payload = json.loads(line)
        indexed = build_index_unit(payload, version.document_id.value)
        units.append(
            {
                "unit_id": indexed.unit_id,
                "position": position,
                "document_key": version.document_id.value,
                "section_code": indexed.section_code,
                "kind": indexed.kind,
                "query_text": indexed.query_text,
                "payload_json": line.decode("utf-8"),
                "payload": payload,
            }
        )
    products = [
        {"yj_code": code.value, "section_code": unit.section_code.value}
        for code in sorted(version.yj_codes, key=lambda code: code.value)
        for unit in project_active_attachment(document, frozenset({code}))
    ]
    return units, products
