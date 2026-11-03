"""Tests for LangGraphChatAgentAdapter (Native Tool Calling & Mandatory Tools)."""

from __future__ import annotations

from typing import Any

import pytest
from backend.application.chat.interfaces.agent_orchestrator import (
    AgentOrchestrator,
)
from backend.application.chat.interfaces.llm_provider import LLMProvider
from backend.application.chat.interfaces.medical_tool import (
    ToolExecutionInput,
    ToolExecutionResult,
)
from backend.application.chat.queries.models import ChatMessage, ChatResponse
from backend.application.retrieval.queries.models import Evidence
from backend.infrastructure.agent.langgraph_chat_agent_adapter import (
    LangGraphChatAgentAdapter,
    LLMProviderChatModelAdapter,
)
from backend.infrastructure.package_insert_definitions.definition_assembly import (
    get_package_insert_definitions,
)
from backend.tests.application.retrieval.test_evidence_collection import (
    make_evidence,
)
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool as lc_tool


class MockToolCallingModel:
    """Native Tool Calling をシミュレートするテスト用モデル"""

    def __init__(
        self,
        tool_calls_sequence: list[list[dict[str, Any]]],
    ) -> None:
        self.tool_calls_sequence = tool_calls_sequence
        self.call_count = 0
        self.bound_tools: list[Any] = []
        self.received_messages: list[Any] = []

    def bind_tools(self, tools: list[Any]) -> MockToolCallingModel:
        self.bound_tools = tools
        return self

    async def ainvoke(
        self, messages: list[Any], config: dict[str, Any] | None = None
    ) -> AIMessage:
        self.received_messages = list(messages)
        if any(isinstance(m, ToolMessage) for m in messages):
            tool_outputs = [
                str(m.content) for m in messages if isinstance(m, ToolMessage)
            ]
            return AIMessage(content=f"回答: {' / '.join(tool_outputs)}")

        if self.call_count < len(self.tool_calls_sequence):
            calls = self.tool_calls_sequence[self.call_count]
            self.call_count += 1
            if calls:
                return AIMessage(content="", tool_calls=calls)

        return AIMessage(content="ツールを呼ばずに直接回答しました。")


class MockMedicalTool:
    """MedicalTool インターフェースを満たすテスト用ツール"""

    def __init__(
        self,
        name: str,
        sources: list[Evidence],
        notices: list[str] | None = None,
        is_mandatory: bool = False,
        needs_clarification: bool = False,
        stream_internally: bool = True,
    ) -> None:
        self.name = name
        self.description = f"Mock tool {name}"
        self.sources = sources
        self.notices = notices or []
        self.is_mandatory = is_mandatory
        self.needs_clarification = needs_clarification
        self.stream_internally = stream_internally
        self.executed = False

    async def execute(self, input_data: ToolExecutionInput) -> ToolExecutionResult:
        self.executed = True
        if self.stream_internally and input_data.on_sources and self.sources:
            await input_data.on_sources(self.sources)
        return ToolExecutionResult(
            tool_name=self.name,
            sources=self.sources,
            intent="general",
            notices=self.notices,
            needs_clarification=self.needs_clarification,
        )


@pytest.mark.asyncio
async def test_agent_automatically_runs_mandatory_tool() -> None:
    mandatory_evidence = [make_evidence("man_1", excerpt="必須添付文書情報")]
    mandatory_tool = MockMedicalTool(
        "essential_tool", mandatory_evidence, notices=["必須注意"], is_mandatory=True
    )
    model = MockToolCallingModel(tool_calls_sequence=[[]])

    adapter = LangGraphChatAgentAdapter(tools=[mandatory_tool], model=model)
    assert isinstance(adapter, AgentOrchestrator)

    conversation = [ChatMessage(role="user", content="ロキソニンの注意事項は？")]
    response = await adapter.run(conversation, ["1149001F1010"])

    assert mandatory_tool.executed is True
    assert len(response.sources) == 1
    assert response.sources[0].unit_id.value == "man_1"
    assert "必須注意" in response.notices
    assert response.retrieval_strategy == "langgraph_agent"


@pytest.mark.asyncio
async def test_agent_registers_tools_and_model_calls_one_natively() -> None:
    test_evidence = [make_evidence("pi_1", excerpt="併用禁忌の記載")]
    package_tool = MockMedicalTool("package_insert", test_evidence)

    tool_call = {
        "id": "call_123",
        "name": "package_insert",
        "args": {"query": "ロキソニン 併用禁忌"},
    }
    model = MockToolCallingModel(tool_calls_sequence=[[tool_call]])

    adapter = LangGraphChatAgentAdapter(tools=[package_tool], model=model)
    assert isinstance(adapter, AgentOrchestrator)

    conversation = [ChatMessage(role="user", content="ロキソニンの併用禁忌を教えて")]
    published_sources: list[list[Evidence]] = []

    async def on_sources(sources: list[Evidence]) -> None:
        published_sources.append(sources)

    response = await adapter.run(
        conversation,
        ["1149001F1010"],
        on_sources=on_sources,
    )

    assert package_tool.executed is True
    assert isinstance(response, ChatResponse)
    assert len(response.sources) == 1
    assert response.sources[0].unit_id.value == "pi_1"
    assert "package_insert" in response.answer
    assert len(published_sources) >= 1


@pytest.mark.asyncio
async def test_agent_calls_multiple_tools_natively_when_model_requests_them() -> None:
    tool_a = MockMedicalTool(
        "package_insert", [make_evidence("pi_1", excerpt="添付文書情報")]
    )
    tool_b = MockMedicalTool(
        "alternative_drug",
        [make_evidence("alt_1", excerpt="代替薬候補")],
        notices=["代替薬の注意事項"],
    )

    calls = [
        {"id": "call_1", "name": "package_insert", "args": {"query": "ロキソニン"}},
        {"id": "call_2", "name": "alternative_drug", "args": {"query": "ロキソニン"}},
    ]
    model = MockToolCallingModel(tool_calls_sequence=[calls])

    adapter = LangGraphChatAgentAdapter(tools=[tool_a, tool_b], model=model)
    conversation = [ChatMessage(role="user", content="ロキソニンと代替薬")]
    response = await adapter.run(conversation, ["1149001F1010"])

    assert tool_a.executed is True
    assert tool_b.executed is True
    assert len(response.sources) == 2
    assert "代替薬の注意事項" in response.notices


@pytest.mark.asyncio
async def test_agent_directly_answers_when_model_does_not_call_tools() -> None:
    tool_a = MockMedicalTool("package_insert", [make_evidence("pi_1", excerpt="記載")])
    model = MockToolCallingModel(tool_calls_sequence=[[]])

    adapter = LangGraphChatAgentAdapter(tools=[tool_a], model=model)
    conversation = [ChatMessage(role="user", content="こんにちは")]
    response = await adapter.run(conversation, [])

    assert tool_a.executed is False
    assert "ツールを呼ばずに直接回答しました" in response.answer
    assert len(response.sources) == 0


@pytest.mark.asyncio
async def test_agent_supports_native_langchain_tool() -> None:
    """LangChain @tool デコレータで作られたツールもそのまま登録可能であることを確認"""

    @lc_tool
    def simple_calculator(a: int, b: int) -> int:
        """簡単な計算を行います。"""
        return a + b

    call = {
        "id": "calc_call",
        "name": "simple_calculator",
        "args": {"a": 2, "b": 3},
    }
    model = MockToolCallingModel(tool_calls_sequence=[[call]])

    adapter = LangGraphChatAgentAdapter(tools=[simple_calculator], model=model)
    conversation = [ChatMessage(role="user", content="2+3を計算して")]
    response = await adapter.run(conversation, [])

    assert "5" in response.answer


@pytest.mark.asyncio
async def test_agent_clarification_skips_model() -> None:
    """医薬品が特定できない等で needs_clarification=True の場合、LLMを呼ばずに確認応答を返すことを検証"""
    clarification_tool = MockMedicalTool(
        "package_insert",
        sources=[],
        notices=["対象医薬品を@医薬品から選択してください。"],
        is_mandatory=True,
        needs_clarification=True,
    )
    model = MockToolCallingModel(tool_calls_sequence=[[]])

    adapter = LangGraphChatAgentAdapter(tools=[clarification_tool], model=model)
    conversation = [ChatMessage(role="user", content="ロキソニン")]
    response = await adapter.run(conversation, [])

    assert clarification_tool.executed is True
    # LLMモデルは一度も呼ばれていないこと（ハルシネーションの防止）
    assert model.call_count == 0
    assert response.needs_clarification is True
    assert "対象医薬品を@医薬品から選択してください。" in response.answer


@pytest.mark.asyncio
async def test_agent_grounded_system_prompt_with_answer_prompt_policy() -> None:
    """answer_prompt_policy が設定された場合、LLMへグラウンディングされた指示プロンプトが渡されることを検証"""
    definitions = get_package_insert_definitions()
    evidence = [make_evidence("ev_1", excerpt="1日2回食後に投与すること。")]
    mandatory_tool = MockMedicalTool(
        "package_insert",
        sources=evidence,
        is_mandatory=True,
    )
    model = MockToolCallingModel(tool_calls_sequence=[[]])

    adapter = LangGraphChatAgentAdapter(
        tools=[mandatory_tool],
        model=model,
        answer_prompt_policy=definitions.answer_prompt_policy,
    )
    conversation = [ChatMessage(role="user", content="用法用量を教えて")]
    await adapter.run(conversation, ["1149001F1010"])

    assert model.call_count == 1
    # LLMに渡された最初のメッセージが SystemMessage であり、公式ルールと根拠を含んでいること
    assert len(model.received_messages) >= 1
    first_msg = model.received_messages[0]
    assert isinstance(first_msg, SystemMessage)
    assert "あなたは薬剤師向けの電子添文検索支援アシスタントです。" in first_msg.content
    assert "1日2回食後に投与すること。" in first_msg.content


@pytest.mark.asyncio
async def test_all_tools_emit_sources_via_on_sources_sequentially() -> None:
    """ツールが内部で on_sources を呼ばない場合でも、グラフが完了時に即時 on_sources を実行することを検証"""
    evidence = [make_evidence("ev_batch", excerpt="バッチ取得された根拠")]
    non_streaming_tool = MockMedicalTool(
        "batch_tool",
        sources=evidence,
        is_mandatory=True,
        stream_internally=False,  # 内部ストリーミング未実装ツールを模擬
    )
    model = MockToolCallingModel(tool_calls_sequence=[[]])

    adapter = LangGraphChatAgentAdapter(tools=[non_streaming_tool], model=model)
    conversation = [ChatMessage(role="user", content="情報取得")]

    streamed_batches: list[list[Evidence]] = []

    async def on_sources(sources: list[Evidence]) -> None:
        streamed_batches.append(sources)

    response = await adapter.run(
        conversation,
        ["1149001F1010"],
        on_sources=on_sources,
    )

    assert len(streamed_batches) == 1
    assert streamed_batches[0][0].unit_id.value == "ev_batch"
    assert len(response.sources) == 1


@pytest.mark.asyncio
async def test_llm_provider_chat_model_adapter() -> None:
    """LLMProviderChatModelAdapter が LLMProvider を正しく ainvoke 可能なモデルへ適合させることを検証"""

    class DummyLLMProvider(LLMProvider):
        async def stream_response(self, messages, model=None):
            yield "これは"
            yield "テスト"
            yield "回答です。"

    adapter_model = LLMProviderChatModelAdapter(DummyLLMProvider())
    res = await adapter_model.ainvoke([SystemMessage(content="プロンプト")])
    assert res.content == "これはテスト回答です。"
