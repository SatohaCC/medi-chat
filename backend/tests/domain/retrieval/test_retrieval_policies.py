"""DM-02: 定義の格納順によらず全分類を取得する。"""

import json

import pytest
from backend.domain.retrieval.services import (
    detect_fixed_keyword_criteria as _detect_fixed_keyword_criteria,
)
from backend.domain.retrieval.services import detect_intents_from_keywords
from backend.infrastructure.package_insert_definitions.loader import (
    DEFINITIONS_PATH,
    load_package_insert_definitions,
)


@pytest.mark.parametrize("reversed_intents", [False, True])
@pytest.mark.parametrize(
    ("message", "intent"),
    [
        ("副作用と併用について", ("interaction", "adverse_events", "indications")),
        ("妊娠可能な人は？", ("reproductive_potential", "pregnancy")),
        ("妊娠中は？", ("pregnancy",)),
        ("こんにちは", ()),
    ],
)
def test_all_fixed_keywords_independent_of_storage_order(
    message, intent, reversed_intents, tmp_path
):
    payload = json.loads(DEFINITIONS_PATH.read_text(encoding="utf-8"))
    if reversed_intents:
        payload["intents"] = dict(reversed(list(payload["intents"].items())))
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    catalog = load_package_insert_definitions(path)
    assert (
        detect_intents_from_keywords(message, intent_policy=catalog.intent_policy)
        == intent
    )
    criteria = _detect_fixed_keyword_criteria(message, catalog.intent_policy)
    for item in criteria:
        assert item.intent is not None
    assert (
        tuple(item.intent.value for item in criteria if item.intent is not None)
        == intent
    )
    for item in criteria:
        assert item.intent is not None
        assert item.source == "logic"
        assert tuple(
            code.value for code in item.section_codes
        ) == catalog.intent_policy.section_codes_for_intent(item.intent.value)
