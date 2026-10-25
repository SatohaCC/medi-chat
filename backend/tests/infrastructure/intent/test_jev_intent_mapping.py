"""DM-03–07: 外側のSDK JSON解釈と公開情報保持。"""

from copy import deepcopy

import pytest
from backend.application.chat.queries.models import ChatMessage
from backend.application.chat.queries.policies.answer_prompt import (
    build_answer_messages,
)
from backend.application.chat.queries.services.reply_preparation import prepare_reply
from backend.application.retrieval.queries.models import (
    IntentCandidate,
    IntentRequest,
    IntentResult,
)
from backend.application.retrieval.queries.services.intent_detection import (
    detect_jev_criteria,
)
from backend.application.retrieval.values import IntentName, Probability
from backend.infrastructure.intent.jev_intent_mapping import map_jev_intent_result
from backend.infrastructure.package_insert_definitions.definition_assembly import (
    get_package_insert_definitions,
)
from backend.tests.application.chat.test_answer_preparation import MedicineReader
from backend.tests.support.retrieval_snapshot import FixedSnapshotProvider


class Classifier:
    def __init__(self, result):
        self.result = result

    async def classify(self, request):
        return self.result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload", "available", "expected", "sections"),
    [
        (None, False, None, ()),
        (None, True, None, ()),
        ({}, True, {}, ()),
        ({"error": "SDK failed"}, True, {"error": "SDK failed"}, ()),
        (
            {"metadata": [None]},
            True,
            {"metadata": [None], "qualifying_intents": []},
            (),
        ),
        (
            {"answers": {"intent": "warnings"}},
            True,
            {"answers": {"intent": "warnings"}, "qualifying_intents": []},
            (),
        ),
        (
            {"answers": {"intent": {"probabilities": []}}},
            True,
            {"answers": {"intent": {"probabilities": []}}, "qualifying_intents": []},
            (),
        ),
    ],
)
async def test_unavailable_missing_and_error_information_is_preserved(
    payload, available, expected, sections
):
    before = deepcopy(payload)
    result = map_jev_intent_result(payload, is_available=available)
    detection = await detect_jev_criteria(
        Classifier(result),
        IntentRequest("質問"),
        intent_policy=get_package_insert_definitions().intent_policy,
    )
    assert detection.raw_response == expected
    assert (
        tuple(
            code.value
            for condition in detection.search_criteria
            for code in condition.section_codes
        )
        == sections
    )
    assert payload == before


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("probabilities", "choice", "intents", "sections"),
    [
        ({"warnings": 0.199999}, None, [], ()),
        ({"warnings": 0.20}, None, ["warnings"], ("1",)),
        ({"warnings": 0.200001}, None, ["warnings"], ("1",)),
        (
            {"dosage": 0.8, "warnings": 0.3},
            None,
            ["dosage", "warnings"],
            ("6", "7", "1"),
        ),
        ({"warnings": 0.1}, "dosage", ["dosage"], ("6", "7")),
        ({"warnings": 0.3}, "dosage", ["warnings"], ("1",)),
        ({"general_or_other": 0.9}, None, [], ()),
        (
            {"unknown_intent": 0.9, "warnings": 0.3},
            None,
            ["unknown_intent", "warnings"],
            ("1",),
        ),
        ({}, "unknown_intent", ["unknown_intent"], ()),
    ],
)
async def test_candidates_and_unknown_information_preserve_existing_selection(
    probabilities, choice, intents, sections
):
    payload = {
        "answers": {"intent": {"probabilities": probabilities, "choice": choice}},
        "metadata": {"values": [True, None, {"unknown": "原文"}]},
    }
    before = deepcopy(payload)
    result = map_jev_intent_result(payload)
    detection = await detect_jev_criteria(
        Classifier(result),
        IntentRequest("質問"),
        intent_policy=get_package_insert_definitions().intent_policy,
    )
    assert detection.raw_response == {**before, "qualifying_intents": intents}
    assert (
        tuple(
            code.value
            for condition in detection.search_criteria
            for code in condition.section_codes
        )
        == sections
    )
    if sections:
        assert detection.search_criteria[0].intent is not None
        assert detection.search_criteria[0].intent.value == intents[0]
    assert payload == before


class EmptyExtractor:
    def extract_keywords(self, text: str) -> tuple[str, ...]:
        return ()


class RecordingReader:
    def __init__(self):
        self.conditions = []

    async def search(self, criteria, medicines):
        self.conditions.append(criteria)
        return ()


@pytest.mark.asyncio
async def test_opaque_public_json_does_not_control_business_selection_or_prompt():
    catalog = get_package_insert_definitions()
    conversation = [ChatMessage(role="user", content="質問")]
    replies = []
    requests = []
    for payload in [
        {"answers": {"intent": {"choice": "dosage"}}},
        {"opaque": [True, None]},
    ]:
        reader = RecordingReader()
        result = IntentResult(
            is_available=True,
            candidates=(IntentCandidate(IntentName("warnings"), Probability(0.3)),),
            raw_response=payload,
            publish_selection=True,
        )
        reply = await prepare_reply(
            conversation,
            ["1234567A0000"],
            snapshot_provider=FixedSnapshotProvider(MedicineReader(), reader),
            intent_classifier=Classifier(result),
            keyword_extractor=EmptyExtractor(),
            intent_policy=catalog.intent_policy,
        )
        assert reply.intent == "warnings"
        assert reply.jev_response == {**payload, "qualifying_intents": ["warnings"]}
        replies.append(reply)
        requests.append(reader.conditions)
    assert requests[0] == requests[1]
    assert [
        tuple(code.value for code in condition.section_codes)
        for condition in requests[0]
    ] == [("1", "2", "8"), ("1",)]
    replies[1].jev_response = {"qualifying_intents": ["dosage", "interaction"]}
    assert build_answer_messages(
        replies[0], conversation, answer_prompt_policy=catalog.answer_prompt_policy
    ) == build_answer_messages(
        replies[1], conversation, answer_prompt_policy=catalog.answer_prompt_policy
    )
