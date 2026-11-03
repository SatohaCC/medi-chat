"""Integration tests for LangGraph chat agent and ChatQueries."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence
from typing import Any

import pytest
from backend.application.chat.interfaces.medical_tool import (
    ToolExecutionInput,
    ToolExecutionResult,
)
from backend.application.chat.queries.chat import ChatQueries
from backend.application.chat.queries.models import (
    ChatMessage,
)
from backend.application.chat.queries.services.package_insert_tools import (
    PackageInsertTools,
)
from backend.application.indexing.queries.models import DocumentRevision
from backend.application.indexing.values import SearchUnitId, SearchUnitKind
from backend.application.medicine.queries.models import RegisteredMedicine
from backend.application.retrieval.queries.models import (
    Evidence,
    EvidenceSection,
    IntentCandidate,
    IntentRequest,
    IntentResult,
)
from backend.application.retrieval.values import (
    EvidenceExcerpt,
    IntentName,
    Probability,
)
from backend.domain.foundation.json_types import JsonValue
from backend.domain.medicine.entities import MedicineProduct
from backend.domain.medicine.identifiers import YjCode
from backend.domain.medicine.primitives import BrandName, GenericName
from backend.domain.medicine.value_objects import MedicineNames
from backend.domain.package_insert.identifiers import DocumentId
from backend.domain.package_insert.primitives import PmdaUrl
from backend.domain.package_insert.value_objects import (
    MedicineDocumentReference,
    PackageInsertProductRevision,
)
from backend.infrastructure.agent.langgraph_chat_agent_adapter import (
    LangGraphChatAgentAdapter,
)
from backend.infrastructure.package_insert_definitions.definition_assembly import (
    get_package_insert_definitions,
)
from backend.tests.application.retrieval.test_evidence_collection import (
    make_evidence,
)
from backend.tests.support.retrieval_snapshot import FixedSnapshotProvider
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage


class MockAgentToolCallingModel:
    def __init__(self) -> None:
        self.call_count = 0

    def bind_tools(self, tools: list[Any]) -> MockAgentToolCallingModel:
        return self

    async def ainvoke(
        self, messages: list[Any], config: dict[str, Any] | None = None
    ) -> AIMessage:
        if any(isinstance(m, ToolMessage) for m in messages):
            return AIMessage(content="AI回答テキスト")

        user_content = next(
            (str(m.content) for m in reversed(messages) if isinstance(m, HumanMessage)),
            "",
        )
        if "ガイドライン" in user_content or "指針" in user_content:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "call_gl",
                        "name": "guideline_search",
                        "args": {"query": user_content},
                    }
                ],
            )
        return AIMessage(content="AI回答テキスト")


class MockLLMProvider:
    async def stream_response(
        self, messages: list[dict[str, str]], model: str | None = None
    ) -> AsyncIterator[str]:
        yield "LLMストリーム回答"


class DummyMedicineReader:
    def __init__(self, medicines: Sequence[RegisteredMedicine] = ()) -> None:
        self._medicines = tuple(medicines)

    async def get_by_yj_code(self, yj_code: str) -> MedicineProduct | None:
        for m in self._medicines:
            if m.yj_code and m.yj_code.value == yj_code:
                return m.medicine
        return None

    async def read_medicines(self) -> tuple[RegisteredMedicine, ...]:
        return self._medicines


class DummyEvidenceReader:
    async def search(self, criteria: Any, medicines: Any) -> tuple[Evidence, ...]:
        return (make_evidence("pi_1", excerpt="添付文書の相互作用記載"),)

    async def find_units(self, *args: Any, **kwargs: Any) -> list[Evidence]:
        return [make_evidence("pi_1", excerpt="添付文書の相互作用記載")]


class DummyIntentClassifier:
    is_available = True

    async def classify(self, request: IntentRequest) -> IntentResult:
        return IntentResult(
            is_available=True,
            candidates=(
                IntentCandidate(
                    intent=IntentName("interaction"),
                    probability=Probability(0.9),
                ),
            ),
            choice="interaction",
            publish_selection=True,
        )

    async def aclose(self) -> None:
        pass


class DummyKeywordExtractor:
    def extract_keywords(self, text: str) -> tuple[str, ...]:
        return ("ロキソニン",)


class DummyOnDemandTool:
    """オンデマンド（is_mandatory=False）ツールのテスト用モック"""

    name: str = "guideline_search"
    description: str = "臨床ガイドライン情報を検索します。"
    is_mandatory: bool = False

    async def execute(self, input_data: ToolExecutionInput) -> ToolExecutionResult:
        ev = Evidence(
            unit_id=SearchUnitId.from_value("gl_1"),
            document_id=DocumentId.from_value("doc_gl_1"),
            product_name=None,
            generic_name=None,
            product_yj_codes=(),
            document_revision=DocumentRevision({}),
            section=EvidenceSection({"code": "GL", "title": "診療ガイドライン"}),
            kind=SearchUnitKind("text"),
            excerpt=EvidenceExcerpt("ガイドライン推奨情報"),
            url=None,
            columns=None,
            references=(),
        )
        if input_data.on_sources:
            await input_data.on_sources([ev])
        return ToolExecutionResult(
            tool_name=self.name,
            sources=[ev],
            intent="general",
            notices=["【ガイドライン参照】専門医の判断を優先してください。"],
        )


@pytest.fixture
def chat_queries_with_langgraph() -> ChatQueries:
    defs = get_package_insert_definitions()
    alt_medicine = RegisteredMedicine(
        medicine=MedicineProduct(
            yj_code=YjCode("1141007F1063"),
            names=MedicineNames(
                generic_name=GenericName("アセトアミノフェン"),
                brand_name=BrandName("カロナール錠200"),
            ),
        ),
        reference=MedicineDocumentReference(
            document_id=DocumentId("doc_2"),
            pmda_url=PmdaUrl("https://example.test"),
            revision=PackageInsertProductRevision({}),
        ),
    )
    target_medicine = RegisteredMedicine(
        medicine=MedicineProduct(
            yj_code=YjCode("1149001F1010"),
            names=MedicineNames(
                generic_name=GenericName("ロキソプロフェンナトリウム水和物"),
                brand_name=BrandName("ロキソニン錠60mg"),
            ),
        ),
        reference=MedicineDocumentReference(
            document_id=DocumentId("doc_1"),
            pmda_url=PmdaUrl("https://example.test"),
            revision=PackageInsertProductRevision({}),
        ),
    )
    med_reader = DummyMedicineReader([alt_medicine, target_medicine])
    snapshot = FixedSnapshotProvider(
        med_reader,
        DummyEvidenceReader(),
    )
    intent_cls = DummyIntentClassifier()
    kw_ext = DummyKeywordExtractor()

    package_tools = PackageInsertTools(
        intent_classifier=intent_cls,
        keyword_extractor=kw_ext,
        intent_policy=defs.intent_policy,
        retrieval_policy=defs.retrieval_policy,
        snapshot_provider=snapshot,
    )
    on_demand_tool = DummyOnDemandTool()

    model = MockAgentToolCallingModel()
    adapter = LangGraphChatAgentAdapter(
        tools=[on_demand_tool], mandatory_tool_provider=package_tools, model=model
    )

    return ChatQueries(
        intent_classifier=intent_cls,
        keyword_extractor=kw_ext,
        intent_policy=defs.intent_policy,
        retrieval_policy=defs.retrieval_policy,
        answer_prompt_policy=defs.answer_prompt_policy,
        provider_factory=lambda _: MockLLMProvider(),
        snapshot_provider=snapshot,
        agent_orchestrator=adapter,
    )


@pytest.mark.asyncio
async def test_chat_queries_prepares_reply_via_langgraph_for_normal_question(
    chat_queries_with_langgraph: ChatQueries,
) -> None:
    queries = chat_queries_with_langgraph
    conversation = [ChatMessage(role="user", content="ロキソニンの相互作用は？")]
    published_sources: list[list[Evidence]] = []

    async def on_sources(sources: list[Evidence]) -> None:
        published_sources.append(sources)

    reply = await queries.prepare_reply(
        conversation,
        ["1149001F1010"],
        on_logic_sources=on_sources,
    )

    assert reply.retrieval_strategy == "langgraph_agent"
    assert reply.answer == "AI回答テキスト"
    assert len(reply.sources) >= 1
    assert reply.sources[0].unit_id.value == "pi_1"
    assert len(published_sources) >= 1

    chunks = []
    async for chunk in queries.stream_answer(
        reply,
        conversation,
        provider_name="mock",
        model_name="mock",
    ):
        chunks.append(chunk)

    assert "".join(chunks) == "AI回答テキスト"


@pytest.mark.asyncio
async def test_chat_queries_publishes_retrieval_completion_before_agent_model():
    events: list[tuple[str, Any]] = []
    model_started = asyncio.Event()
    model_release = asyncio.Event()
    jev_response: dict[str, JsonValue] = {"query": "completed"}

    class MandatoryRetrievalTool:
        name = "mandatory_retrieval"
        description = "必須の根拠取得"
        is_mandatory = True

        async def execute(self, input_data: ToolExecutionInput) -> ToolExecutionResult:
            events.append(("retrieval_finished", None))
            return ToolExecutionResult(
                tool_name=self.name,
                jev_response=jev_response,
            )

    class SlowModel:
        async def ainvoke(
            self, messages: Sequence[Any], config: dict[str, Any] | None = None
        ) -> AIMessage:
            events.append(("answer_model_started", None))
            model_started.set()
            await model_release.wait()
            return AIMessage(content="回答")

    definitions = get_package_insert_definitions()
    adapter = LangGraphChatAgentAdapter(
        tools=[MandatoryRetrievalTool()], model=SlowModel()
    )
    queries = ChatQueries(
        intent_classifier=DummyIntentClassifier(),
        keyword_extractor=DummyKeywordExtractor(),
        intent_policy=definitions.intent_policy,
        answer_prompt_policy=definitions.answer_prompt_policy,
        provider_factory=lambda _: MockLLMProvider(),
        snapshot_provider=FixedSnapshotProvider(
            DummyMedicineReader(), DummyEvidenceReader()
        ),
        agent_orchestrator=adapter,
    )

    async def publish_retrieval_complete(response: dict[str, Any] | None) -> None:
        events.append(("retrieval_complete", response))

    task = asyncio.create_task(
        queries.prepare_reply(
            [ChatMessage(role="user", content="質問")],
            ["1149001F1010"],
            on_retrieval_complete=publish_retrieval_complete,
        )
    )
    try:
        await asyncio.wait_for(model_started.wait(), timeout=1)
        assert events == [
            ("retrieval_finished", None),
            ("retrieval_complete", jev_response),
            ("answer_model_started", None),
        ]
        assert not task.done(), "回答生成が終わる前に取得完了を通知する"
        model_release.set()
        reply = await asyncio.wait_for(task, timeout=5)
    finally:
        model_release.set()
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    assert reply.jev_response == jev_response


@pytest.mark.asyncio
async def test_chat_queries_prepares_and_streams_on_demand_tool_reply(
    chat_queries_with_langgraph: ChatQueries,
) -> None:
    queries = chat_queries_with_langgraph
    conversation = [
        ChatMessage(role="user", content="ロキソニンのガイドライン情報を教えて")
    ]
    published_sources: list[list[Evidence]] = []

    async def on_sources(sources: list[Evidence]) -> None:
        published_sources.append(sources)

    reply = await queries.prepare_reply(
        conversation,
        ["1149001F1010"],
        on_logic_sources=on_sources,
    )

    assert reply.retrieval_strategy == "langgraph_agent"
    assert reply.answer == "AI回答テキスト"
    assert any(s.unit_id.value == "gl_1" for s in reply.sources)
    assert any("ガイドライン" in n for n in reply.notices)
    assert len(published_sources) >= 1


@pytest.fixture
def chat_queries_with_mandatory_langgraph() -> ChatQueries:
    defs = get_package_insert_definitions()
    target_medicine = RegisteredMedicine(
        medicine=MedicineProduct(
            yj_code=YjCode("1149001F1010"),
            names=MedicineNames(
                generic_name=GenericName("ロキソプロフェンナトリウム水和物"),
                brand_name=BrandName("ロキソニン錠60mg"),
            ),
        ),
        reference=MedicineDocumentReference(
            document_id=DocumentId("doc_1"),
            pmda_url=PmdaUrl("https://example.test"),
            revision=PackageInsertProductRevision({}),
        ),
    )
    med_reader = DummyMedicineReader([target_medicine])
    snapshot = FixedSnapshotProvider(
        med_reader,
        DummyEvidenceReader(),
    )
    intent_cls = DummyIntentClassifier()
    kw_ext = DummyKeywordExtractor()

    package_tools = PackageInsertTools(
        intent_classifier=intent_cls,
        keyword_extractor=kw_ext,
        intent_policy=defs.intent_policy,
        retrieval_policy=defs.retrieval_policy,
        snapshot_provider=snapshot,
    )

    model = MockAgentToolCallingModel()
    adapter = LangGraphChatAgentAdapter(
        mandatory_tool_provider=package_tools, model=model
    )

    return ChatQueries(
        intent_classifier=intent_cls,
        keyword_extractor=kw_ext,
        intent_policy=defs.intent_policy,
        retrieval_policy=defs.retrieval_policy,
        answer_prompt_policy=defs.answer_prompt_policy,
        provider_factory=lambda _: MockLLMProvider(),
        snapshot_provider=snapshot,
        agent_orchestrator=adapter,
    )


@pytest.mark.asyncio
async def test_chat_queries_langgraph_clarification_for_unregistered_medicine(
    chat_queries_with_mandatory_langgraph: ChatQueries,
) -> None:
    queries = chat_queries_with_mandatory_langgraph
    conversation = [ChatMessage(role="user", content="ロキソニンの相互作用は？")]

    reply = await queries.prepare_reply(
        conversation,
        ["9999999F9999"],
    )

    assert reply.needs_clarification is True
    assert (
        "検索対象の構造化データに登録されているYJコードを指定してください。"
        in reply.answer
    )
    assert reply.sources == []
