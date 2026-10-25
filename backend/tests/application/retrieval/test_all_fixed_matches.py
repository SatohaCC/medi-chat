import pytest
from backend.application.retrieval.queries.policies.selection import (
    detect_fixed_keyword_criteria,
)
from backend.infrastructure.package_insert_definitions.definition_assembly import (
    get_package_insert_definitions,
)


@pytest.mark.parametrize(
    "message,expected",
    [
        (
            "副作用と飲み合わせを教えて",
            {"interaction", "adverse_events", "indications"},
        ),
        ("併用禁忌について", {"interaction", "contraindications"}),
        ("副作用、副作用と副作用", {"adverse_events", "indications"}),
        ("妊娠可能な人は？", {"reproductive_potential", "pregnancy"}),
        ("ＣＹＰと副作用", {"pharmacokinetics", "adverse_events", "indications"}),
        ("こんにちは", set()),
    ],
)
def test_all_matching_classifications_are_selected_once(message, expected):
    policy = get_package_insert_definitions().intent_policy
    results = detect_fixed_keyword_criteria(message, policy)
    for item in results:
        assert item.intent is not None
    assert {
        item.intent.value for item in results if item.intent is not None
    } == expected
    assert len(results) == len(expected)
    for item in results:
        assert item.intent is not None
        assert item.source == "logic"
        assert tuple(
            code.value for code in item.section_codes
        ) == policy.section_codes_for_intent(item.intent.value)
