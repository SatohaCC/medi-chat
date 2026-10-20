"""実adapterとport Fakeを同じ純粋な利用先へ交換できることを検証する。"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Mapping
from copy import deepcopy
from dataclasses import asdict, dataclass, fields, replace

import pytest
from backend.application.chat.answer_preparation import prepare_reply
from backend.application.chat.answer_prompt_builder import build_answer_messages
from backend.application.chat.answer_question import answer_question
from backend.application.chat.answer_stream import stream_answer
from backend.application.chat.chat_models import ChatMessage, ChatResponse
from backend.application.medicine.product_models import (
    RegisteredMedicine,
    ResolvedMedicine,
)
from backend.application.retrieval.intent_contracts import IntentRequest, IntentResult
from backend.application.retrieval.jev_detector import (
    JevDetectionResult,
    detect_jev_criteria,
)
from backend.application.retrieval.morphology_detector import detect_morphology_criteria
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.attachment.primitives import PmdaUrl
from backend.domain.attachment.value_objects import (
    AttachmentProductRevision,
    MedicineDocumentReference,
)
from backend.domain.foundation.json_types import JsonValue
from backend.domain.foundation.primitives.primitives import (
    BaseFiniteFloat,
    BaseString,
)
from backend.domain.medicine.entities import MedicineProduct
from backend.domain.medicine.identifiers import YjCode
from backend.domain.medicine.primitives import (
    BrandName,
    GenericName,
    MatchedAlias,
)
from backend.domain.medicine.value_objects import MedicineMatch as DomainMedicineMatch
from backend.domain.medicine.value_objects import MedicineNames
from backend.domain.retrieval.identifiers import SearchUnitId
from backend.domain.retrieval.primitives import (
    DetectionSource,
    IntentName,
    Probability,
    SearchKeyword,
    SearchSectionCode,
)
from backend.domain.retrieval.repositories import (
    EvidenceSearchTarget,
)
from backend.domain.retrieval.value_objects import (
    DocumentRevision,
    Evidence,
    EvidenceSection,
    IntentCandidate,
    SearchCriteria,
)
from backend.infrastructure.intent.jev_classifier import JevIntentClassifier
from backend.infrastructure.morphology.janome_keyword_extractor import (
    JanomeKeywordExtractor,
)
from backend.infrastructure.package_insert_definitions.loader import (
    get_package_insert_definitions,
)
from backend.presentation.chat_dto_mapper import chat_response_to_api
from backend.tests.support.paths import FIXTURES_ROOT


class FakeSdkError(RuntimeError):
    """adapter内で純粋なエラー情報へ変換するSDK側の例外。"""


class FakeSdkResponse:
    def __init__(self, payload: dict[str, JsonValue]) -> None:
        self.payload = payload

    def model_dump(self) -> dict[str, JsonValue]:
        return deepcopy(self.payload)


class RecordingSdkClient:
    def __init__(self, payload: dict[str, JsonValue], *, fail: bool = False) -> None:
        self.payload = payload
        self.fail = fail
        self.states: list[dict[str, JsonValue]] = []

    async def system_one(
        self, *, state: dict[str, JsonValue], questions: dict[str, object]
    ) -> FakeSdkResponse:
        self.states.append(deepcopy(state))
        if self.fail:
            raise FakeSdkError("Jev test transport failed")
        return FakeSdkResponse(self.payload)


class RecordingIntentClassifier:
    def __init__(self, result: IntentResult) -> None:
        self.result = result
        self.requests: list[IntentRequest] = []

    async def classify(self, request: IntentRequest) -> IntentResult:
        self.requests.append(request)
        return deepcopy(self.result)


def _assert_json_values(value: object) -> None:
    if isinstance(value, dict):
        assert type(value) is dict
        for key, item in value.items():
            assert type(key) is str
            _assert_json_values(item)
    elif isinstance(value, list):
        assert type(value) is list
        for item in value:
            _assert_json_values(item)
    else:
        assert type(value) in (type(None), bool, int, float, str), (
            f"意図判定の純粋値に外部型が残った: {type(value)}"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", ["normal", "unavailable", "sdk_error"])
@pytest.mark.parametrize("target", ["adapter", "consumer"])
async def test_intent_classifier_contract(
    scenario: str, target: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload: dict[str, JsonValue] = {
        "answers": {
            "intent": {"choice": "warnings", "probabilities": {"warnings": 0.9}}
        },
        "metadata": [True, None, {"round": 1}],
    }
    request = IntentRequest(
        question="警告は？",
        medicines=(
            ResolvedMedicine(
                medicine=DomainMedicineMatch(
                    generic_name=GenericName("テスト成分"),
                    brand_names=tuple(BrandName(value) for value in ("テスト錠",)),
                    yj_codes=tuple(YjCode(value) for value in ("1234567A0000",)),
                    matched_aliases=tuple(
                        MatchedAlias(value) for value in ("テスト錠",)
                    ),
                ),
                document_ids=("document-1",),
            ),
        ),
    )
    if scenario == "normal":
        expected_intent = IntentResult(
            is_available=True,
            raw_response=payload,
            candidates=(IntentCandidate(IntentName("warnings"), Probability(0.9)),),
            choice="warnings",
            publish_selection=True,
        )
        expected_detection = JevDetectionResult(
            search_criteria=[
                SearchCriteria(
                    source=DetectionSource("jev"),
                    intent=IntentName("warnings"),
                    section_codes=(SearchSectionCode("1"),),
                )
            ],
            raw_response={**payload, "qualifying_intents": ["warnings"]},
            qualifying_intents=("warnings",),
        )
    elif scenario == "unavailable":
        expected_intent = IntentResult(is_available=False, raw_response=None)
        expected_detection = JevDetectionResult()
    else:
        expected_intent = IntentResult(
            is_available=True, raw_response={"error": "Jev test transport failed"}
        )
        expected_detection = JevDetectionResult(
            raw_response={"error": "Jev test transport failed"}
        )

    catalog = get_package_insert_definitions()
    adapter = JevIntentClassifier(
        api_key="", classification_settings=catalog.jev_settings
    )
    sdk = RecordingSdkClient(payload, fail=scenario == "sdk_error")
    monkeypatch.setattr(adapter, "_client", None if scenario == "unavailable" else sdk)
    fake = RecordingIntentClassifier(expected_intent)

    if target == "adapter":
        result = await adapter.classify(request)
        assert type(result) is IntentResult
        assert type(result.is_available) is bool
        assert result == expected_intent
        _assert_json_values(result.raw_response)
    else:
        fake_detection = await detect_jev_criteria(
            fake, request, intent_policy=catalog.intent_policy
        )
        adapter_detection = await detect_jev_criteria(
            adapter, request, intent_policy=catalog.intent_policy
        )
        assert type(fake_detection) is JevDetectionResult
        assert type(adapter_detection) is JevDetectionResult
        assert fake_detection == adapter_detection == expected_detection
        assert fake.requests == [request]
        assert fake.requests[0] is request
        for detection in (fake_detection, adapter_detection):
            assert all(
                type(criteria) is SearchCriteria
                for criteria in detection.search_criteria
            )
            _assert_json_values(detection.raw_response)

    if scenario == "unavailable":
        assert sdk.states == []
    else:
        assert len(sdk.states) == 1
        assert sdk.states[0]["question"] == "警告は？"
    assert "qualifying_intents" not in payload


class RecordingKeywordExtractor:
    def __init__(self, keywords: tuple[str, ...]) -> None:
        self.keywords = keywords
        self.texts: list[str] = []

    def extract_keywords(self, text: str) -> tuple[str, ...]:
        self.texts.append(text)
        return self.keywords


@pytest.mark.parametrize("target", ["adapter", "consumer"])
@pytest.mark.parametrize(
    ("message", "excluded_terms", "cleaned", "expected_keywords", "expected_criteria"),
    [
        pytest.param(
            "頭痛がする",
            (),
            "頭痛がする",
            ("頭痛",),
            SearchCriteria(
                source=DetectionSource("keyword"), keywords=(SearchKeyword("頭痛"),)
            ),
            id="nouns",
        ),
        pytest.param(
            "テスト薬で頭痛 薬",
            ("テスト", "テスト薬", "テスト薬", "薬"),
            " で頭痛 薬",
            ("頭痛",),
            SearchCriteria(
                source=DetectionSource("keyword"), keywords=(SearchKeyword("頭痛"),)
            ),
            id="excluded_terms",
        ),
        pytest.param(
            "副作用",
            (),
            "副作用",
            (),
            None,
            id="empty_result",
        ),
    ],
)
def test_keyword_extractor_contract(
    target: str,
    message: str,
    excluded_terms: tuple[str, ...],
    cleaned: str,
    expected_keywords: tuple[str, ...],
    expected_criteria: SearchCriteria | None,
) -> None:
    adapter = JanomeKeywordExtractor(
        search_policy=get_package_insert_definitions().text_search_policy,
        morphology_settings=get_package_insert_definitions().morphology_settings,
    )
    fake = RecordingKeywordExtractor(expected_keywords)

    if target == "adapter":
        keywords = adapter.extract_keywords(cleaned)
        assert type(keywords) is tuple
        assert all(type(keyword) is str for keyword in keywords)
        assert keywords == expected_keywords
    else:
        fake_result = detect_morphology_criteria(fake, message, excluded_terms)
        adapter_result = detect_morphology_criteria(adapter, message, excluded_terms)
        assert fake_result == adapter_result == expected_criteria
        assert fake.texts == [cleaned]
        for result in (fake_result, adapter_result):
            if result is not None:
                assert type(result) is SearchCriteria
                assert type(result.keywords) is tuple
                assert all(
                    isinstance(keyword.value, str) for keyword in result.keywords
                )
                assert result.source == "keyword"
                assert result.intent is None
                assert result.section_codes == ()


def fixed_medicines():
    return (
        RegisteredMedicine(
            medicine=MedicineProduct(
                yj_code=YjCode("1234567A0000"),
                names=MedicineNames(
                    brand_name=BrandName("テスト薬"),
                    generic_name=GenericName("テスト成分"),
                    english_name=None,
                    hiragana_name=None,
                ),
            ),
            reference=MedicineDocumentReference(
                document_id=DocumentId("test_001"),
                pmda_url=PmdaUrl("https://example.test/package-insert"),
                revision=AttachmentProductRevision({}),
            ),
        ),
    )


@dataclass(frozen=True)
class AnswerPreparationCase:
    conversation: tuple[ChatMessage, ...]
    product_yj_codes: list[str]
    intent_response: dict[str, JsonValue]
    expected_reply: ChatResponse
    expected_messages: list[dict[str, str]]


@pytest.fixture
def answer_preparation_case() -> AnswerPreparationCase:
    # 固定oracleは旧実行の証跡から保存する。継続テストは旧moduleをimportしない。
    raw: object = json.loads(
        (FIXTURES_ROOT / "answer_preparation_tc05.json").read_text(encoding="utf-8")
    )
    assert isinstance(raw, dict)
    conversation = (
        ChatMessage(role="system", content="外側のsystemはLLM入力へ重複させない"),
        ChatMessage(role="user", content="テスト薬について"),
        ChatMessage(role="assistant", content="確認しました"),
        ChatMessage(role="user", content="テスト薬の副作用と頭痛について"),
    )
    intent_response: dict[str, JsonValue] = {
        "answers": {
            "intent": {
                "choice": "adverse_events",
                "probabilities": {"adverse_events": 0.9},
            }
        }
    }
    expected_reply = ChatResponse(
        answer="関連する添付文書の記載を3件取得しました。対象項目: 11.1 重大な副作用。",
        intent="adverse_events",
        retrieval_strategy="three_detectors",
        resolved_medicines=[
            ResolvedMedicine(
                medicine=DomainMedicineMatch(
                    generic_name=GenericName("テスト成分"),
                    brand_names=tuple(BrandName(value) for value in ("テスト薬",)),
                    yj_codes=tuple(YjCode(value) for value in ("1234567A0000",)),
                ),
                document_ids=("test_001",),
            )
        ],
        sources=[
            Evidence(
                unit_id=SearchUnitId(f"test_001:{index:03d}"),
                document_id=DocumentId("test_001"),
                product_name="テスト薬",
                generic_name="テスト成分",
                product_yj_codes=(YjCode("1234567A0000"),),
                document_revision=DocumentRevision({}),
                section=EvidenceSection({"code": "11.1", "title": "重大な副作用"}),
                kind="text",
                excerpt=f"頭痛に注意してください。記載{index}",
                url="https://example.test/package-insert",
                retrieved_by=frozenset(DetectionSource),
            )
            for index in range(3)
        ],
        jev_response={
            **deepcopy(intent_response),
            "qualifying_intents": ["adverse_events"],
        },
        qualifying_intents=("adverse_events",),
    )
    assert [asdict(message) for message in conversation] == raw["conversation"]
    assert raw["product_yj_codes"] == ["1234567A0000"]
    assert raw["intent_response"] == intent_response
    assert chat_response_to_api(expected_reply).model_dump(mode="json") == raw["reply"]
    raw_messages = raw["llm_messages"]
    assert isinstance(raw_messages, list)
    expected_messages: list[dict[str, str]] = []
    for message in raw_messages:
        assert isinstance(message, dict)
        role, content = message["role"], message["content"]
        assert isinstance(role, str) and isinstance(content, str)
        expected_messages.append({"role": role, "content": content})
    return AnswerPreparationCase(
        conversation,
        ["1234567A0000"],
        intent_response,
        expected_reply,
        expected_messages,
    )


class RecordingMedicineReader:
    def __init__(self, medicines: tuple[RegisteredMedicine, ...]) -> None:
        self.medicines = deepcopy(medicines)
        self.calls = 0

    async def read_medicines(self) -> tuple[RegisteredMedicine, ...]:
        self.calls += 1
        return deepcopy(self.medicines)


class RecordingEvidenceReader:
    def __init__(
        self, sources: list[Evidence], medicines: list[ResolvedMedicine]
    ) -> None:
        self.sources = deepcopy(sources)
        self.medicines = deepcopy(medicines)
        self.requests: list[
            tuple[SearchCriteria, tuple[EvidenceSearchTarget, ...]]
        ] = []

    async def search(
        self, criteria: SearchCriteria, medicines: tuple[EvidenceSearchTarget, ...]
    ) -> tuple[Evidence, ...]:
        assert list(medicines) == self.medicines
        assert criteria in (
            SearchCriteria(
                source=DetectionSource("logic"),
                intent=IntentName("indications"),
                section_codes=(SearchSectionCode("4"), SearchSectionCode("5")),
            ),
            SearchCriteria(
                source=DetectionSource("logic"),
                intent=IntentName("adverse_events"),
                section_codes=(
                    SearchSectionCode("11"),
                    SearchSectionCode("11.1"),
                    SearchSectionCode("11.2"),
                ),
            ),
            SearchCriteria(
                source=DetectionSource("jev"),
                intent=IntentName("adverse_events"),
                section_codes=(
                    SearchSectionCode("11"),
                    SearchSectionCode("11.1"),
                    SearchSectionCode("11.2"),
                ),
            ),
            SearchCriteria(
                source=DetectionSource("keyword"), keywords=(SearchKeyword("頭痛"),)
            ),
        )
        self.requests.append((criteria, deepcopy(medicines)))
        return tuple(
            replace(source, retrieved_by=frozenset({criteria.source}))
            for source in self.sources
        )


class RecordingAnswerProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[list[dict[str, str]], str | None]] = []

    async def stream_response(
        self, messages: list[dict[str, str]], model: str | None = None
    ) -> AsyncIterator[str]:
        self.calls.append((deepcopy(messages), model))
        yield "同じ"
        yield "回答"


def _assert_answer_values(value: object) -> None:
    pure_types = (
        ChatMessage,
        ChatResponse,
        RegisteredMedicine,
        MedicineProduct,
        MedicineNames,
        MedicineDocumentReference,
        ResolvedMedicine,
        DomainMedicineMatch,
        Evidence,
        IntentRequest,
    )
    if isinstance(value, Mapping) and type(value) is not dict:
        _assert_json_values(dict(value))
    elif isinstance(value, pure_types):
        assert type(value) in pure_types
        for field in fields(value):
            _assert_answer_values(getattr(value, field.name))
    elif isinstance(value, (list, tuple, frozenset)):
        assert type(value) in (list, tuple, frozenset)
        for item in value:
            _assert_answer_values(item)
    else:
        if isinstance(
            value,
            (
                BaseFiniteFloat,
                BaseString,
                BrandName,
                GenericName,
                MatchedAlias,
                DetectionSource,
            ),
        ):
            return
        _assert_json_values(value)


async def _assert_prepared_answer(
    reply: ChatResponse, case: AnswerPreparationCase
) -> None:
    assert type(reply) is ChatResponse
    assert reply == case.expected_reply
    _assert_answer_values(reply)
    messages = build_answer_messages(
        reply,
        case.conversation,
        answer_prompt_policy=get_package_insert_definitions().answer_prompt_policy,
    )
    assert messages == case.expected_messages
    _assert_json_values(messages)
    provider = RecordingAnswerProvider()
    chunks = [
        chunk async for chunk in stream_answer(provider, messages, model="tc05-model")
    ]
    assert chunks == ["同じ", "回答"]
    assert provider.calls == [(case.expected_messages, "tc05-model")]


@pytest.mark.asyncio
async def test_answer_preparation_accepts_pure_reader_ports(
    answer_preparation_case: AnswerPreparationCase,
) -> None:
    case = answer_preparation_case
    fake_medicine = RecordingMedicineReader(fixed_medicines())
    fake_evidence = RecordingEvidenceReader(
        case.expected_reply.sources, case.expected_reply.resolved_medicines
    )
    medicine_reader = fake_medicine
    evidence_reader = fake_evidence
    intent = RecordingIntentClassifier(
        IntentResult(
            is_available=True,
            raw_response=deepcopy(case.intent_response),
            candidates=(
                IntentCandidate(IntentName("adverse_events"), Probability(0.9)),
            ),
            choice="adverse_events",
            publish_selection=True,
        )
    )
    keywords = RecordingKeywordExtractor(("頭痛",))
    conversation_before = deepcopy(case.conversation)
    codes_before = list(case.product_yj_codes)
    reply = await prepare_reply(
        case.conversation,
        case.product_yj_codes,
        medicine_reader=medicine_reader,
        evidence_reader=evidence_reader,
        intent_classifier=intent,
        keyword_extractor=keywords,
        intent_policy=get_package_insert_definitions().intent_policy,
    )
    assert case.conversation == conversation_before
    assert case.product_yj_codes == codes_before
    assert len(intent.requests) == 1
    assert intent.requests[0].question == "テスト薬の副作用と頭痛について"
    _assert_answer_values(intent.requests[0])
    assert keywords.texts == [" の副作用と頭痛について"]
    assert fake_medicine.calls == 1
    assert len(fake_evidence.requests) == 4
    assert {
        criteria.intent.value
        for criteria, _ in fake_evidence.requests
        if criteria.source == "logic" and criteria.intent is not None
    } == {"adverse_events", "indications"}
    assert {criteria.source for criteria, _ in fake_evidence.requests} == {
        "logic",
        "jev",
        "keyword",
    }
    await _assert_prepared_answer(reply, case)


@pytest.mark.asyncio
async def test_answer_preparation_prompt_preserves_fixed_llm_input(
    answer_preparation_case: AnswerPreparationCase,
) -> None:
    # 準備入口の失敗でpromptが未到達にならないよう、同じ固定replyを直接観測する。
    await _assert_prepared_answer(
        deepcopy(answer_preparation_case.expected_reply), answer_preparation_case
    )


class RecordingProviderFactory:
    def __init__(self) -> None:
        self.names: list[str | None] = []
        self.provider = RecordingAnswerProvider()

    def __call__(self, name: str | None) -> RecordingAnswerProvider:
        self.names.append(name)
        return self.provider


@pytest.mark.asyncio
async def test_clarification_does_not_create_or_call_provider() -> None:
    fake_medicine = RecordingMedicineReader(fixed_medicines())
    fake_evidence = RecordingEvidenceReader([], [])
    medicine_reader = fake_medicine
    evidence_reader = fake_evidence
    conversation = (ChatMessage(role="user", content="副作用を教えて"),)
    product_yj_codes = ["0000000A0000"]
    conversation_before = deepcopy(conversation)
    codes_before = list(product_yj_codes)
    intent = RecordingIntentClassifier(IntentResult(is_available=False))
    keywords = RecordingKeywordExtractor(())
    factory = RecordingProviderFactory()
    # 旧response_builderの確認応答全文・全項目を固定する。
    expected = ChatResponse(
        answer="指定されたYJコードのすべてに対応する電子添文が、現在の検索データにありません。",
        intent="adverse_events, indications",
        retrieval_strategy="product_code_lookup",
        needs_clarification=True,
        notices=["検索対象の構造化データに登録されているYJコードを指定してください。"],
    )
    reply = await answer_question(
        conversation,
        product_yj_codes,
        medicine_reader=medicine_reader,
        evidence_reader=evidence_reader,
        intent_classifier=intent,
        keyword_extractor=keywords,
        intent_policy=get_package_insert_definitions().intent_policy,
        answer_prompt_policy=get_package_insert_definitions().answer_prompt_policy,
        provider_factory=factory,
        provider_name="openai",
        model_name="gpt-6-luna",
    )
    assert reply == expected
    _assert_answer_values(reply)
    assert conversation == conversation_before
    assert product_yj_codes == codes_before
    assert factory.names == []
    assert factory.provider.calls == []
    assert fake_evidence.requests == []
    assert fake_medicine.calls == 1
