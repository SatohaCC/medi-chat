"""Registration v3 headings survive encoding and reads of historical payloads."""

import json
import re
from copy import deepcopy
from typing import cast

import pytest
from backend.application.indexing.attachment_projection import project_active_attachment
from backend.domain.medicine.identifiers import YjCode
from backend.domain.retrieval.primitives import DetectionSource
from backend.infrastructure.index_payloads import (
    encode_registered_units,
    registered_unit_text,
)
from backend.infrastructure.package_insert_definitions.loader import (
    get_package_insert_definitions,
)
from backend.infrastructure.persistence import registration_schema
from backend.infrastructure.persistence.evidence_reader import _read_evidence
from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder
from backend.tests.support.paths import PROJECT_ROOT
from sqlalchemy import create_engine, literal, select
from sqlalchemy.sql.selectable import Select

CASES = [
    ("400093_3962002F2027_1_22", "3962002F3023"),
    ("630004_3339003F5020_1_08", "3339003F5020"),
]


def registered_payload(stem, yj_code):
    source = next((PROJECT_ROOT / "data/pmda/originals").rglob(f"{stem}.xml"))
    document = PmdaXmlDecoder().decode(source.read_bytes()).document
    units = project_active_attachment(document, frozenset({YjCode(yj_code)}))
    unit = next(unit for unit in units if unit.section_code.value == "10.1")
    return json.loads(encode_registered_units(document, (unit,)))


def historical_source(stem, yj_code):
    payload = registered_payload(stem, yj_code)
    # This is the old v3 encoder's exact omission, as seen in the reported screen.
    payload["text"] = re.sub(r"<thead>.*?</thead>", "", payload["text"], flags=re.S)
    assert "<th" not in payload["text"]
    return payload


def historical_evidence(stem, yj_code):
    """Exercise the production SQLite read boundary with an old registration payload."""
    payload = historical_source(stem, yj_code)
    engine = create_engine("sqlite://")
    registration_schema.registration_version_artifacts.create(engine)
    try:
        with engine.begin() as connection:
            connection.execute(
                registration_schema.registration_version_artifacts.insert().values(
                    version_id=payload["version_id"],
                    document_payload_json="{}",
                )
            )
            statement = select(
                literal(json.dumps(payload)).label("payload_json"),
                literal(None).label("document_payload_json"),
            )
            sources = _read_evidence(
                connection,
                cast("Select[str, str | None]", statement),
                DetectionSource.LOGIC,
                get_package_insert_definitions().text_search_policy,
                frozenset({yj_code}),
            )
            assert len(sources) == 1
            return sources[0].to_dict()
    finally:
        engine.dispose()


@pytest.mark.parametrize("stem,yj_code", CASES)
def test_registration_encoder_and_historical_evidence_keep_original_column_titles(
    stem, yj_code
):
    payload = registered_payload(stem, yj_code)
    for heading in ("薬剤名", "臨床症状・措置方法", "機序・危険因子"):
        assert f'<th scope="col">{heading}</th>' in payload["text"]

    historical = historical_source(stem, yj_code)
    before = deepcopy(historical)
    restored = registered_unit_text(historical)
    assert historical == before  # read-only recovery, no DB/artifact rewrite
    assert restored == payload["text"]
    assert restored.count("<tbody>") == restored.count("<thead>")
    table = next(block for block in historical["blocks"] if block["kind"] == "table")
    assert table["rows"][0][0]["text"].split("\n")[0] in restored
    assert historical_evidence(stem, yj_code)["excerpt"] == payload["text"]


def test_generic_header_rows_are_not_duplicated_and_legacy_text_is_unchanged():
    unit = {
        "schema_version": "medi-chat.pmda-sections.v3",
        "blocks": [
            {
                "kind": "table",
                "columns": ["見出し"],
                "rows": [
                    [{"text": "見出し", "rowspan": 1, "colspan": 2}],
                    [{"text": "CrCl <30 & 原文", "rowspan": 2, "colspan": 1}],
                ],
            }
        ],
    }
    text = registered_unit_text(unit)
    assert text.count("見出し") == 1
    assert 'rowspan="2" colspan="1"' in text
    assert "CrCl &lt;30 &amp; 原文" in text
    assert registered_unit_text({"text": "旧形式\n原文"}) == "旧形式\n原文"
