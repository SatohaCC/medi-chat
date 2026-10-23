"""DM-02: 定義の格納順によらず全分類を取得する。"""

from dataclasses import replace

import pytest
from backend.application.retrieval.queries.policies.selection import (
    detect_fixed_keyword_criteria as _detect_fixed_keyword_criteria,
)
from backend.application.retrieval.queries.policies.selection import (
    detect_intents_from_keywords,
)
from backend.application.retrieval.queries.policies.standard import (
    DEFAULT_INTENT_POLICY,
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
    policy = (
        replace(
            DEFAULT_INTENT_POLICY,
            intents=tuple(reversed(DEFAULT_INTENT_POLICY.intents)),
        )
        if reversed_intents
        else DEFAULT_INTENT_POLICY
    )
    assert detect_intents_from_keywords(message, intent_policy=policy) == intent
    criteria = _detect_fixed_keyword_criteria(message, policy)
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
        ) == policy.section_codes_for_intent(item.intent.value)
