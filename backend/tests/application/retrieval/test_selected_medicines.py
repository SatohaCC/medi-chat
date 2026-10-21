import pytest
from backend.application.retrieval.intent_contracts import IntentResult
from backend.application.retrieval.retrieve_evidence import retrieve_evidence
from backend.infrastructure.package_insert_definitions.loader import (
    get_package_insert_definitions,
)
from backend.tests.application.chat.test_answer_preparation import MedicineReader
from backend.tests.application.retrieval.test_evidence_collection import make_evidence


class NoJev:
    async def classify(self, request):
        return IntentResult(is_available=False)


class NoKeywords:
    def extract_keywords(self, text):
        return ()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message", ["商品の副作用", "ロキソニンの副作用", "商品と未知薬の併用"]
)
async def test_selected_codes_alone_determine_targets(message):
    searched = []

    class Reader:
        async def search(self, criteria, medicines):
            searched.extend(
                code for medicine in medicines for code in medicine.yj_codes
            )
            return (make_evidence(),)

    result = await retrieve_evidence(
        message,
        ["1234567A0000"],
        medicine_reader=MedicineReader(),
        evidence_reader=Reader(),
        intent_classifier=NoJev(),
        keyword_extractor=NoKeywords(),
        intent_policy=get_package_insert_definitions().intent_policy,
    )
    assert not result.needs_clarification
    assert result.retrieval_strategy == "three_detectors"
    assert searched and set(searched) == {"1234567A0000"}


@pytest.mark.asyncio
async def test_typed_name_without_selection_does_not_resolve_a_product():
    class Reader:
        async def search(self, criteria, medicines):
            raise AssertionError("Unselected medicines must not be searched")

    result = await retrieve_evidence(
        "1234567A0000の副作用",
        [],
        medicine_reader=MedicineReader(),
        evidence_reader=Reader(),
        intent_classifier=NoJev(),
        keyword_extractor=NoKeywords(),
        intent_policy=get_package_insert_definitions().intent_policy,
    )
    assert result.needs_clarification
    assert result.resolved_medicines == []
