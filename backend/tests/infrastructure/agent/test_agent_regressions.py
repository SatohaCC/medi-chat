"""Production agent regressions: grounding, clarification and execution isolation."""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import replace

import pytest
from backend.application.chat.interfaces.medical_tool import ToolExecutionResult
from backend.application.chat.queries.models import ChatMessage
from backend.application.retrieval.values import DetectionSource
from backend.infrastructure.agent.langgraph_chat_agent_adapter import (
    LangGraphChatAgentAdapter,
    LLMProviderChatModelAdapter,
)
from backend.tests.infrastructure.agent.test_langgraph_chat_agent import (
    MockMedicalTool,
    MockToolCallingModel,
    get_package_insert_definitions,
    make_evidence,
)
from langchain_core.messages import AIMessage, SystemMessage


@pytest.mark.asyncio
async def test_on_demand_evidence_is_grounded_before_final_answer():
    evidence = make_evidence("on_demand", excerpt="TEST_GROUNDING")
    tool = MockMedicalTool("lookup", [evidence])
    model = MockToolCallingModel(
        [[{"id": "call", "name": "lookup", "args": {"query": "q"}}]]
    )
    adapter = LangGraphChatAgentAdapter(
        [tool],
        model=model,
        answer_prompt_policy=get_package_insert_definitions().answer_prompt_policy,
    )
    response = await adapter.run([ChatMessage(role="user", content="q")])
    prompt = next(
        m.content for m in model.received_messages if isinstance(m, SystemMessage)
    )
    assert "TEST_GROUNDING" in prompt
    assert "on_demand" in prompt
    assert response.sources == [evidence]


@pytest.mark.asyncio
async def test_on_demand_clarification_stops_model_loop():
    tool = MockMedicalTool(
        "lookup", [], notices=["テスト対象を指定してください"], needs_clarification=True
    )
    model = MockToolCallingModel(
        [[{"id": "call", "name": "lookup", "args": {"query": "q"}}]]
    )
    adapter = LangGraphChatAgentAdapter([tool], model=model)
    response = await adapter.run([ChatMessage(role="user", content="q")])
    assert response.needs_clarification
    assert response.answer == "テスト対象を指定してください"
    assert not any(isinstance(m, SystemMessage) for m in model.received_messages)


@pytest.mark.asyncio
async def test_request_model_factory_is_lazy_and_isolated():
    created = []

    @asynccontextmanager
    async def factory(provider, model):
        created.append((provider, model))
        yield MockToolCallingModel([[]])

    tool = MockMedicalTool("required", [], is_mandatory=True, needs_clarification=True)
    adapter = LangGraphChatAgentAdapter([tool], model_factory=factory)
    conversation = [ChatMessage(role="user", content="q")]
    await adapter.run(conversation, provider_name="openai", model_name="one")
    assert created == []
    tool.needs_clarification = False
    await asyncio.gather(
        adapter.run(conversation, provider_name="openai", model_name="one"),
        adapter.run(conversation, provider_name="gemini", model_name="two"),
    )
    assert sorted(created) == [("gemini", "two"), ("openai", "one")]


@pytest.mark.asyncio
async def test_tool_failure_is_not_converted_to_an_answer():
    class FailingTool(MockMedicalTool):
        async def execute(self, input_data):
            raise RuntimeError("test retrieval failure")

    model = MockToolCallingModel(
        [[{"id": "call", "name": "lookup", "args": {"query": "q"}}]]
    )
    adapter = LangGraphChatAgentAdapter([FailingTool("lookup", [])], model=model)
    with pytest.raises(RuntimeError, match="test retrieval failure"):
        await adapter.run([ChatMessage(role="user", content="q")])


@pytest.mark.asyncio
@pytest.mark.parametrize("timeout", [False, True])
async def test_cancellation_and_timeout_release_request_model(timeout):
    started = asyncio.Event()
    closed = []

    class BlockingModel:
        async def ainvoke(self, messages, config=None):
            started.set()
            await asyncio.Event().wait()

    @asynccontextmanager
    async def factory(provider, model):
        try:
            yield BlockingModel()
        finally:
            closed.append(True)

    adapter = LangGraphChatAgentAdapter(
        [], model_factory=factory, timeout_seconds=0.1 if timeout else 10
    )
    task = asyncio.create_task(adapter.run([ChatMessage(role="user", content="q")]))
    await asyncio.wait_for(started.wait(), 2)
    if not timeout:
        task.cancel()
    with pytest.raises(TimeoutError if timeout else asyncio.CancelledError):
        await task
    assert closed == [True]


@pytest.mark.asyncio
async def test_text_provider_stream_is_closed_immediately_on_cancellation():
    started = asyncio.Event()
    closed = []

    class Provider:
        async def stream_response(self, messages, model=None):
            try:
                yield "partial"
                started.set()
                await asyncio.Event().wait()
            finally:
                closed.append(True)

    model = LLMProviderChatModelAdapter(Provider())
    task = asyncio.create_task(model.ainvoke([]))
    await asyncio.wait_for(started.wait(), 2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert closed == [True]
    with pytest.raises(ValueError, match="does not support tool calling"):
        model.bind_tools([])


@pytest.mark.asyncio
async def test_repeated_tool_calls_are_bounded():
    class LoopingModel:
        calls = 0

        def bind_tools(self, tools):
            return self

        async def ainvoke(self, messages, config=None):
            self.calls += 1
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": f"call_{self.calls}",
                        "name": "lookup",
                        "args": {"query": "q"},
                    }
                ],
            )

    model = LoopingModel()
    adapter = LangGraphChatAgentAdapter(
        [MockMedicalTool("lookup", [])], model=model, max_tool_rounds=2
    )
    with pytest.raises(RuntimeError, match="limit exceeded"):
        await adapter.run([ChatMessage(role="user", content="q")])
    assert model.calls == 3


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        AIMessage(content=""),
        AIMessage(content="partial", response_metadata={"finish_reason": "MAX_TOKENS"}),
    ],
)
async def test_invalid_final_answers_are_not_published(response):
    class Model:
        async def ainvoke(self, messages, config=None):
            return response

    with pytest.raises(ValueError):
        await LangGraphChatAgentAdapter([], model=Model()).run(
            [ChatMessage(role="user", content="q")]
        )


@pytest.mark.asyncio
async def test_concurrent_requests_do_not_share_evidence_or_callbacks():
    class PerRequestTool(MockMedicalTool):
        async def execute(self, input_data):
            await asyncio.sleep(0)
            return ToolExecutionResult(
                tool_name=self.name,
                sources=[make_evidence(input_data.message, excerpt=input_data.message)],
                intent="interaction",
                qualifying_intents=("interaction", "dosage"),
                jev_response={"request": input_data.message},
            )

    prompts = []

    class Model:
        async def ainvoke(self, messages, config=None):
            prompts.append(messages[0].text)
            return AIMessage(content="テスト回答")

    @asynccontextmanager
    async def factory(provider, model):
        yield Model()

    agent = LangGraphChatAgentAdapter(
        [PerRequestTool("required", [], is_mandatory=True)],
        model_factory=factory,
        answer_prompt_policy=get_package_insert_definitions().answer_prompt_policy,
    )

    async def run(label):
        published = []

        async def on_sources(sources):
            published.extend(sources)

        reply = await agent.run(
            [ChatMessage(role="user", content=label)], on_sources=on_sources
        )
        assert [s.unit_id.value for s in reply.sources] == [label]
        assert published == reply.sources
        assert reply.jev_response == {"request": label}
        assert reply.qualifying_intents == ("interaction", "dosage")

    await asyncio.gather(run("REQUEST_A"), run("REQUEST_B"))
    assert len(prompts) == 2
    assert all(("REQUEST_A" in p) != ("REQUEST_B" in p) for p in prompts)


@pytest.mark.asyncio
async def test_duplicate_sources_keep_original_content_and_all_provenance():
    first = replace(
        make_evidence("same", excerpt="FIRST_ORIGINAL"),
        retrieved_by=frozenset({DetectionSource.KEYWORD}),
    )
    second = replace(
        first,
        excerpt=make_evidence(excerpt="SECOND_COPY").excerpt,
        retrieved_by=frozenset({DetectionSource.JEV}),
    )
    agent = LangGraphChatAgentAdapter(
        [
            MockMedicalTool("one", [first], is_mandatory=True),
            MockMedicalTool("two", [second], is_mandatory=True),
        ],
        model=MockToolCallingModel([[]]),
    )
    response = await agent.run([ChatMessage(role="user", content="q")])
    assert len(response.sources) == 1
    assert response.sources[0].excerpt.value == "FIRST_ORIGINAL"
    assert response.sources[0].retrieved_by == {
        DetectionSource.KEYWORD,
        DetectionSource.JEV,
    }
