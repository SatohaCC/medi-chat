"""DM-03/04: 型付き候補の閾値・順位・choice補完。"""

import pytest
from backend.application.retrieval.queries.models import IntentCandidate
from backend.application.retrieval.queries.policies.selection import select_intents
from backend.application.retrieval.values import IntentName, Probability
from backend.infrastructure.package_insert_definitions.definition_assembly import (
    get_package_insert_definitions,
)


@pytest.mark.parametrize(
    ("probability", "expected"), [(0.199999, ()), (0.20, ("1",)), (0.200001, ("1",))]
)
def test_probability_threshold_boundary(probability, expected):
    result = select_intents(
        (IntentCandidate(IntentName("warnings"), Probability(probability)),),
        None,
        intent_policy=get_package_insert_definitions().intent_policy,
    )
    assert tuple(code.value for code in result.section_codes) == expected
    assert tuple(intent.value for intent in result.qualifying_intents) == (
        ("warnings",) if expected else ()
    )


def test_probability_order_and_section_deduplication():
    result = select_intents(
        (
            IntentCandidate(IntentName("warnings"), Probability(0.3)),
            IntentCandidate(IntentName("dosage"), Probability(0.8)),
        ),
        None,
        intent_policy=get_package_insert_definitions().intent_policy,
    )
    assert (result.primary.value if result.primary is not None else None) == "dosage"
    assert tuple(intent.value for intent in result.qualifying_intents) == (
        "dosage",
        "warnings",
    )
    assert tuple(code.value for code in result.section_codes) == ("6", "7", "1")


@pytest.mark.parametrize(
    ("candidates", "choice", "primary", "qualifying", "sections"),
    [
        (
            (IntentCandidate(IntentName("warnings"), Probability(0.1)),),
            "dosage",
            "dosage",
            ("dosage",),
            ("6", "7"),
        ),
        (
            (IntentCandidate(IntentName("warnings"), Probability(0.3)),),
            "dosage",
            "warnings",
            ("warnings",),
            ("1",),
        ),
        (
            (IntentCandidate(IntentName("general_or_other"), Probability(0.9)),),
            None,
            "document_search",
            (),
            (),
        ),
    ],
)
def test_choice_fallback_only_when_no_qualifying_candidate(
    candidates, choice, primary, qualifying, sections
):
    result = select_intents(
        candidates, choice, intent_policy=get_package_insert_definitions().intent_policy
    )
    assert (result.primary.value if result.primary is not None else None) == primary
    assert tuple(intent.value for intent in result.qualifying_intents) == qualifying
    assert tuple(code.value for code in result.section_codes) == sections


def test_custom_probability_threshold():
    result = select_intents(
        (IntentCandidate(IntentName("warnings"), Probability(0.4)),),
        None,
        intent_policy=get_package_insert_definitions().intent_policy,
        threshold=Probability(0.5),
    )
    assert result.qualifying_intents == ()


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -0.1, 1.1])
def test_invalid_threshold_is_rejected_by_probability(value):
    from backend.domain.foundation.exceptions import DomainValidationError

    with pytest.raises(DomainValidationError):
        select_intents(
            (),
            None,
            intent_policy=get_package_insert_definitions().intent_policy,
            threshold=Probability(value),
        )
