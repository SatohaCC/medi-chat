"""Build browser evidence from original XML through the current projection."""

import json

from backend.application.indexing.queries.services.attachment_projection import (
    project_active_attachment,
)
from backend.domain.medicine.identifiers import YjCode
from backend.infrastructure.evidence_mapping import build_evidence
from backend.infrastructure.import_payloads import AttachmentSourceInformation
from backend.infrastructure.index_payloads import encode_registered_units
from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder
from backend.presentation.chat_dto_mapper import evidence_to_api
from backend.tests.support.paths import PROJECT_ROOT


def current_evidence(stem: str, yj_code: str) -> dict:
    source = next((PROJECT_ROOT / "data/pmda/originals").rglob(f"{stem}.xml"))
    decoded = PmdaXmlDecoder().decode(source.read_bytes())
    assert isinstance(decoded.source_info, AttachmentSourceInformation)
    units = project_active_attachment(decoded.document, frozenset({YjCode(yj_code)}))
    unit = next(unit for unit in units if unit.section_code.value == "10")
    payload = json.loads(encode_registered_units(decoded.document, (unit,)))
    evidence = build_evidence(payload, decoded.source_info.document, "logic")
    return evidence_to_api(evidence).model_dump()


if __name__ == "__main__":
    print(
        json.dumps(
            [
                current_evidence("400093_3962002F2027_1_22", "3962002F3023"),
                current_evidence("630004_3339003F5020_1_08", "3339003F5020"),
            ],
            ensure_ascii=False,
        )
    )
