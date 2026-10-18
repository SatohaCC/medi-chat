"""実adapterとport Fakeを同じ純粋な利用先へ交換できることを検証する。"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Mapping
from copy import deepcopy
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path

import pytest
from backend.application.chat.answer_preparation import prepare_reply
from backend.application.chat.answer_prompt_builder import build_answer_messages
from backend.application.chat.answer_question import answer_question
from backend.application.chat.answer_stream import stream_answer
from backend.application.chat.chat_models import ChatMessage, ChatResponse
from backend.application.indexing.index_builder import build_index
from backend.application.indexing.index_contracts import IndexSourceReader, IndexWriter
from backend.application.indexing.index_models import (
    IndexBuildResult,
    IndexDocument,
    IndexUnit,
    SourceSnapshot,
)
from backend.application.medicine.product_catalog import MedicineCatalog
from backend.application.medicine.product_contracts import RegisteredMedicineReader
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
from backend.domain.medicine.value_objects import MedicineMatch as DomainMedicineMatch
from backend.domain.retrieval.identifiers import SearchUnitId
from backend.domain.retrieval.primitives import (
    DetectionSource,
    IntentName,
    Probability,
    SearchKeyword,
    SearchSectionCode,
)
from backend.domain.retrieval.repositories import (
    EvidenceRepository,
    EvidenceSearchTarget,
)
from backend.domain.retrieval.services import merge_evidence
from backend.domain.retrieval.value_objects import (
    DocumentRevision,
    Evidence,
    EvidenceSection,
    IntentCandidate,
    SearchCriteria,
)
from backend.infrastructure.index_payloads import build_index_document, build_index_unit
from backend.infrastructure.intent.jev_classifier import JevIntentClassifier
from backend.infrastructure.morphology.janome_keyword_extractor import (
    JanomeKeywordExtractor,
)
from backend.infrastructure.package_insert_definitions.loader import (
    get_package_insert_definitions,
)
from backend.infrastructure.persistence import schema
from backend.infrastructure.persistence.evidence_reader import SqlAlchemyEvidenceReader
from backend.infrastructure.persistence.index_writer import SqlAlchemyIndexWriter
from backend.infrastructure.persistence.medicine_reader import SqlAlchemyMedicineReader
from backend.infrastructure.sources.file_index_source import FileIndexSourceReader
from backend.presentation.chat_dto_mapper import chat_response_to_api
from backend.tests.infrastructure.persistence.test_package_insert_index import (
    migrated_index as migrated_index,
)
from backend.tests.support.paths import FIXTURES_ROOT
from backend.tests.support.storage_fixtures import make_search_payload
from sqlalchemy import select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError


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
                    generic_name="テスト成分",
                    brand_names=("テスト錠",),
                    yj_codes=("1234567A0000",),
                    matched_aliases=("テスト錠",),
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


class RecordingIndexSource:
    def __init__(self, snapshot: SourceSnapshot) -> None:
        self.snapshot = deepcopy(snapshot)
        self.calls = 0

    def read_snapshot(self) -> SourceSnapshot:
        self.calls += 1
        return deepcopy(self.snapshot)


class MemoryIndexWriter:
    def __init__(self) -> None:
        self.received: list[SourceSnapshot] = []
        self.saved: SourceSnapshot | None = None

    def replace(self, snapshot: SourceSnapshot) -> IndexBuildResult:
        self.received.append(snapshot)
        self.saved = deepcopy(snapshot)
        return IndexBuildResult(len(snapshot.documents), len(snapshot.units))


def _assert_index_values(value: object) -> None:
    pure_types = (
        SourceSnapshot,
        IndexDocument,
        IndexUnit,
        RegisteredMedicine,
        MedicineProduct,
        MedicineDocumentReference,
        IndexBuildResult,
    )
    if isinstance(value, Mapping) and type(value) is not dict:
        _assert_json_values(dict(value))
    elif isinstance(value, pure_types):
        assert type(value) in pure_types
        for field in fields(value):
            _assert_index_values(getattr(value, field.name))
    elif isinstance(value, tuple):
        assert type(value) is tuple
        for item in value:
            _assert_index_values(item)
    else:
        if isinstance(
            value,
            (
                BaseFiniteFloat,
                BaseString,
                DetectionSource,
            ),
        ):
            return
        _assert_json_values(value)


def _assert_core_saved_snapshot(engine: Engine, snapshot: SourceSnapshot) -> None:
    # 実DB保存値を比較する。applicationにはRow/Engine/SQLを渡さない。
    with engine.connect() as connection:
        documents = connection.execute(select(schema.documents)).all()
        assert [
            (row.document_key, json.loads(row.payload_json)) for row in documents
        ] == [
            (document.document_id, document.payload) for document in snapshot.documents
        ]
        medicines = connection.execute(select(schema.medicines)).all()
        assert [
            (*tuple(row)[:-1], json.loads(row.revision_json)) for row in medicines
        ] == [
            (
                medicine.document_id.value,
                medicine.yj_code.value if medicine.yj_code is not None else None,
                medicine.brand_name,
                medicine.generic_name,
                medicine.english_name,
                medicine.hiragana_name,
                medicine.pmda_url.value,
                medicine.revision,
            )
            for medicine in snapshot.medicines
        ]
        units = connection.execute(
            select(schema.units).order_by(schema.units.c.unit_id)
        ).all()
        assert [(*tuple(row)[:-1], json.loads(row.payload_json)) for row in units] == [
            (
                unit.unit_id,
                unit.document_id,
                unit.section_code,
                unit.kind,
                unit.payload,
            )
            for unit in snapshot.units
        ]
        fts = connection.execute(
            text(
                "SELECT unit_id, document_key, section_code, kind, query_text, drug_name "
                "FROM unit_fts ORDER BY unit_id"
            )
        ).all()
        assert [tuple(row) for row in fts] == [
            (
                unit.unit_id,
                unit.document_id,
                unit.section_code,
                unit.kind,
                unit.query_text,
                unit.drug_name,
            )
            for unit in snapshot.units
        ]
        assert (
            connection.execute(
                select(schema.index_meta.c.value).where(
                    schema.index_meta.c.key == "source_fingerprint"
                )
            ).scalar_one()
            == snapshot.fingerprint
        )


@pytest.mark.parametrize("source_kind", ["file", "fake"])
@pytest.mark.parametrize("writer_kind", ["core", "memory"])
def test_index_ports_accept_equivalent_snapshots(
    migrated_index: tuple[Path, Engine], source_kind: str, writer_kind: str
) -> None:
    source_dir, engine = migrated_index
    file_source = FileIndexSourceReader(source_dir)
    snapshot = file_source.read_snapshot()
    # 全保存項目は既存fixtureの固定値から期待する。動的fingerprintだけは同じ取得値を渡す。
    document: dict[str, JsonValue] = {
        "schema_version": "medi-chat.pmda-prescription-xml.v2",
        "document": {
            "company_identifier": "test",
            "package_insert_no": "001",
            "generic_name": "テスト成分",
            "products": [{"yj_code": "1234567A0000", "brand_name": "テスト薬"}],
        },
        "source": {"pmda_url": "https://example.test/package-insert"},
    }
    expected = SourceSnapshot(
        documents=(IndexDocument("test_001", document),),
        medicines=(
            RegisteredMedicine(
                medicine=MedicineProduct(
                    yj_code=YjCode("1234567A0000"),
                    brand_name="テスト薬",
                    generic_name="テスト成分",
                    english_name="",
                    hiragana_name="",
                ),
                reference=MedicineDocumentReference(
                    document_id=DocumentId("test_001"),
                    pmda_url=PmdaUrl("https://example.test/package-insert"),
                    revision=AttachmentProductRevision({}),
                ),
            ),
        ),
        units=tuple(
            IndexUnit(
                unit_id=f"test_001:{index:03d}",
                document_id="test_001",
                section_code="11.1",
                kind="text",
                payload=make_search_payload(
                    {
                        "unit_id": f"test_001:{index:03d}",
                        "document_key": "test_001",
                        "product_yj_codes": ["1234567A0000"],
                        "section": {"code": "11.1", "title": "重大な副作用"},
                        "kind": "text",
                        "text": f"頭痛に注意してください。記載{index}",
                    }
                ),
                query_text=f"頭痛に注意してください 記載{index} 重大な副作用",
                drug_name="",
            )
            for index in range(3)
        ),
        fingerprint=snapshot.fingerprint,
    )
    assert snapshot.fingerprint.strip()
    assert snapshot == expected
    _assert_index_values(snapshot)
    fake_source = RecordingIndexSource(expected)
    memory_writer = MemoryIndexWriter()
    source_reader: IndexSourceReader = (
        file_source if source_kind == "file" else fake_source
    )
    writer: IndexWriter = (
        SqlAlchemyIndexWriter(engine) if writer_kind == "core" else memory_writer
    )
    result = build_index(source_reader, writer)
    assert type(result) is IndexBuildResult
    assert result == IndexBuildResult(1, 3)
    _assert_index_values(result)
    if source_kind == "fake":
        assert fake_source.calls == 1
        assert fake_source.snapshot == expected
    if writer_kind == "core":
        _assert_core_saved_snapshot(engine, expected)
    else:
        assert memory_writer.received == [expected]
        assert memory_writer.saved == expected
        _assert_index_values(memory_writer.received[0])
        _assert_index_values(memory_writer.saved)


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
                    generic_name="テスト成分",
                    brand_names=("テスト薬",),
                    yj_codes=("1234567A0000",),
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
@pytest.mark.parametrize("medicine_kind", ["real", "fake"])
@pytest.mark.parametrize("evidence_kind", ["real", "fake"])
async def test_answer_preparation_accepts_real_and_fake_readers(
    migrated_index: tuple[Path, Engine],
    answer_preparation_case: AnswerPreparationCase,
    medicine_kind: str,
    evidence_kind: str,
) -> None:
    source, engine = migrated_index
    case = answer_preparation_case
    snapshot = FileIndexSourceReader(source).read_snapshot()
    assert SqlAlchemyIndexWriter(engine).replace(snapshot) == IndexBuildResult(1, 3)
    fake_medicine = RecordingMedicineReader(snapshot.medicines)
    fake_evidence = RecordingEvidenceReader(
        case.expected_reply.sources, case.expected_reply.resolved_medicines
    )
    medicine_reader: RegisteredMedicineReader = (
        SqlAlchemyMedicineReader(engine) if medicine_kind == "real" else fake_medicine
    )
    evidence_reader: EvidenceRepository = (
        SqlAlchemyEvidenceReader(engine) if evidence_kind == "real" else fake_evidence
    )
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
    if medicine_kind == "fake":
        assert fake_medicine.calls == 1
    if evidence_kind == "fake":
        assert len(fake_evidence.requests) == 3
        assert {criteria.source for criteria, _ in fake_evidence.requests} == {
            "logic",
            "jev",
            "keyword",
        }
    await _assert_prepared_answer(reply, case)


@pytest.mark.asyncio
async def test_multiple_document_ids_are_global_and_collisions_roll_back(
    migrated_index,
):
    source, engine = migrated_index
    first = FileIndexSourceReader(source).read_snapshot()
    second_payload = deepcopy(first.documents[0].payload)
    metadata = second_payload["document"]
    assert isinstance(metadata, dict)
    metadata["company_identifier"] = "second"
    second_document, second_medicines = build_index_document(second_payload)
    assert second_document.document_id == "second_001"
    second_units = []
    for index, unit in enumerate(first.units):
        payload = deepcopy(unit.payload)
        payload.update(unit_id=f"second:{index:03}", document_key="second_001")
        second_units.append(build_index_unit(payload, "second_001"))
    snapshot = SourceSnapshot(
        (*first.documents, second_document),
        (*first.medicines, *second_medicines),
        (*first.units, *second_units),
        "two-document-fixture",
    )
    writer = SqlAlchemyIndexWriter(engine)
    assert writer.replace(snapshot) == IndexBuildResult(2, 6)
    medicines = await SqlAlchemyMedicineReader(engine).read_medicines()
    matches = tuple(
        ResolvedMedicine(
            medicine=DomainMedicineMatch(
                generic_name=group.generic_name,
                brand_names=tuple(group.brand_names),
                yj_codes=tuple(group.yj_codes),
                matched_aliases=tuple(group.matched_aliases),
            ),
            document_ids=tuple(group.document_ids),
        )
        for group in MedicineCatalog(medicines).resolve_medicines("", ["1234567A0000"])
    )
    hits = await SqlAlchemyEvidenceReader(engine).search(
        SearchCriteria(
            source=DetectionSource("logic"), section_codes=(SearchSectionCode("11.1"),)
        ),
        matches,
    )
    sources = merge_evidence(((hits, DetectionSource.LOGIC),))
    response = chat_response_to_api(
        ChatResponse(
            answer="",
            intent="adverse_events",
            retrieval_strategy="three_detectors",
            sources=list(sources),
        )
    )
    payload = response.model_dump(mode="json")
    assert [item["unit_id"] for item in payload["sources"]] == [
        "second:000",
        "second:001",
        "second:002",
        "test_001:000",
        "test_001:001",
        "test_001:002",
    ]
    assert {item["document_id"] for item in payload["sources"]} == {
        "second_001",
        "test_001",
    }
    collision = replace(second_units[0], unit_id="test_001:000")
    conflicting = replace(
        snapshot,
        units=(*first.units, collision, *second_units[1:]),
        fingerprint="collision",
    )
    with pytest.raises(IntegrityError, match="UNIQUE constraint failed: units.unit_id"):
        writer.replace(conflicting)
    preserved = await SqlAlchemyEvidenceReader(engine).search(
        SearchCriteria(
            source=DetectionSource("logic"), section_codes=(SearchSectionCode("11.1"),)
        ),
        matches,
    )
    assert [item.to_dict() for item in preserved] == [item.to_dict() for item in hits]


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
@pytest.mark.parametrize("medicine_kind", ["real", "fake"])
@pytest.mark.parametrize("evidence_kind", ["real", "fake"])
async def test_clarification_does_not_create_or_call_provider(
    migrated_index: tuple[Path, Engine],
    monkeypatch: pytest.MonkeyPatch,
    medicine_kind: str,
    evidence_kind: str,
) -> None:
    source, engine = migrated_index
    snapshot = FileIndexSourceReader(source).read_snapshot()
    assert SqlAlchemyIndexWriter(engine).replace(snapshot) == IndexBuildResult(1, 3)
    fake_medicine = RecordingMedicineReader(snapshot.medicines)
    fake_evidence = RecordingEvidenceReader([], [])
    real_evidence = SqlAlchemyEvidenceReader(engine)
    evidence_requests: list[
        tuple[SearchCriteria, tuple[EvidenceSearchTarget, ...]]
    ] = []
    real_search = real_evidence.search

    async def record_real_search(
        criteria: SearchCriteria, medicines: tuple[EvidenceSearchTarget, ...]
    ) -> tuple[Evidence, ...]:
        evidence_requests.append((criteria, deepcopy(medicines)))
        return await real_search(criteria, medicines)

    monkeypatch.setattr(real_evidence, "search", record_real_search)
    medicine_reader: RegisteredMedicineReader = (
        SqlAlchemyMedicineReader(engine) if medicine_kind == "real" else fake_medicine
    )
    evidence_reader: EvidenceRepository = (
        real_evidence if evidence_kind == "real" else fake_evidence
    )
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
        intent="adverse_events",
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
    assert evidence_requests == []
    assert fake_evidence.requests == []
    if medicine_kind == "fake":
        assert fake_medicine.calls == 1
