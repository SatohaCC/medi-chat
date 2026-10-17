"""DM-02: 固定キーワードの現行優先順位を直接観測する。"""

import json

import pytest
from backend.domain.retrieval.services import (
    detect_fixed_keyword_criteria as _detect_fixed_keyword_criteria,
)
from backend.domain.retrieval.services import detect_intent_from_keywords
from backend.infrastructure.package_insert_definitions.loader import (
    DEFINITIONS_PATH,
    load_package_insert_definitions,
)


@pytest.mark.parametrize("reversed_intents", [False, True])
@pytest.mark.parametrize(
    ("message", "intent"),
    [
        ("副作用と併用について", "interaction"),
        ("妊娠可能な人は？", "reproductive_potential"),
        ("妊娠中は？", "pregnancy"),
        ("こんにちは", "document_search"),
    ],
)
def test_fixed_keyword_priority(message, intent, reversed_intents, tmp_path):
    payload = json.loads(DEFINITIONS_PATH.read_text(encoding="utf-8"))
    if reversed_intents:
        payload["intents"] = dict(reversed(list(payload["intents"].items())))
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    catalog = load_package_insert_definitions(path)
    assert (
        detect_intent_from_keywords(message, intent_policy=catalog.intent_policy)
        == intent
    )
    criteria = _detect_fixed_keyword_criteria(message, catalog.intent_policy)
    if intent == "document_search":
        assert criteria is None
        return
    assert criteria is not None
    assert criteria.source == "logic"
    assert criteria.intent is not None
    assert criteria.intent.value == intent
    assert tuple(
        code.value for code in criteria.section_codes
    ) == catalog.intent_policy.section_codes_for_intent(intent)
