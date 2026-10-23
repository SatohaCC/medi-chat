"""Current search format keeps declared column titles; old formats are rejected."""

import json

import pytest
from backend.application.indexing.queries.services.attachment_projection import (
    project_active_attachment,
)
from backend.domain.medicine.identifiers import YjCode
from backend.infrastructure.index_payloads import (
    encode_registered_units,
    registered_unit_text,
)
from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder
from backend.tests.support.paths import PROJECT_ROOT

CASES = [
    ("400093_3962002F2027_1_22", "3962002F3023"),
    ("630004_3339003F5020_1_08", "3339003F5020"),
]


@pytest.mark.source_data
@pytest.mark.parametrize("stem,yj_code", CASES)
def test_current_encoder_saves_declared_column_titles(stem, yj_code):
    source = next((PROJECT_ROOT / "data/pmda/originals").rglob(f"{stem}.xml"))
    document = PmdaXmlDecoder().decode(source.read_bytes()).document
    units = project_active_attachment(document, frozenset({YjCode(yj_code)}))
    unit = next(unit for unit in units if unit.section_code.value == "10")
    payload = json.loads(encode_registered_units(document, (unit,)))
    assert payload["schema_version"] == "medi-chat.pmda-sections.v4"
    for heading in ("薬剤名", "臨床症状・措置方法", "機序・危険因子"):
        assert f'<th scope="col">{heading}</th>' in payload["text"]
    assert registered_unit_text(payload) == payload["text"]


@pytest.mark.parametrize(
    "version", [None, "medi-chat.pmda-sections.v2", "medi-chat.pmda-sections.v3"]
)
def test_old_search_formats_are_rejected_without_repair(version):
    value = {"schema_version": version, "text": "old body", "blocks": []}
    with pytest.raises(ValueError, match="regenerate"):
        registered_unit_text(value)


def test_current_format_requires_blocks_without_plain_text_fallback():
    with pytest.raises(ValueError, match="structured blocks"):
        registered_unit_text(
            {"schema_version": "medi-chat.pmda-sections.v4", "text": "body"}
        )
