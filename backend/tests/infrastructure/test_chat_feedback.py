"""B05-B16: signed targets and acknowledged, idempotent SDK writes."""

import asyncio
import threading
from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest
from backend.application.chat.commands.submit_feedback import SubmitFeedback
from backend.application.chat.errors import (
    FeedbackForbidden,
    FeedbackTimeout,
    FeedbackUnavailable,
)
from backend.infrastructure.observability.feedback_tokens import SignedFeedbackTokens
from backend.infrastructure.observability.langsmith_feedback_adapter import (
    LangSmithFeedback,
)
from langsmith import Client as SdkClient
from langsmith.utils import (
    LangSmithConflictError,
    LangSmithNotFoundError,
    LangSmithRequestTimeout,
)

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def tokens(clock=lambda: 100):
    return SignedFeedbackTokens(secret=b"s" * 32, audience="test", clock=clock)


class Client:
    def __init__(self):
        self.rows = {}
        self.closed = False
        self.created = []

    def read_project(self, *, project_name):
        assert project_name == "test-project"
        return SimpleNamespace(id=uuid4())

    def update_feedback(self, feedback_id, *, score):
        if feedback_id not in self.rows:
            raise LangSmithNotFoundError("missing")
        self.rows[feedback_id]["score"] = score

    def create_feedback(self, **values):
        feedback_id = values["feedback_id"]
        if feedback_id in self.rows:
            raise LangSmithConflictError("exists")
        self.rows[feedback_id] = values
        self.created.append(values)

    def close(self):
        self.closed = True

    def delete_feedback(self, feedback_id):
        if feedback_id not in self.rows:
            raise LangSmithNotFoundError("missing")
        del self.rows[feedback_id]


async def test_cancel_feedback_is_idempotent_and_can_be_selected_again():
    codec, client = tokens(), Client()
    adapter = LangSmithFeedback(cast(SdkClient, client))
    command = SubmitFeedback(tokens=codec, writer=adapter)
    token = codec.issue(uuid4(), "test-project", "user")
    try:
        await command.execute(token, "user", "up")
        original_id = next(iter(client.rows))
        await command.execute(token, "user", None)
        assert client.rows == {}
        await command.execute(token, "user", None)
        assert client.rows == {}
        await command.execute(token, "user", "down")
        assert list(client.rows) == [original_id]
        assert client.rows[original_id]["score"] == 0
    finally:
        await adapter.aclose()


@pytest.mark.parametrize("rating,score", [("up", 1), ("down", 0)])
async def test_B05_B07_B14_acknowledged_retry_and_change(rating, score):
    codec, client = tokens(), Client()
    adapter = LangSmithFeedback(cast(SdkClient, client))
    command = SubmitFeedback(tokens=codec, writer=adapter)
    run_id = uuid4()
    token = codec.issue(run_id, "test-project", "user")
    try:
        await command.execute(token, "user", rating)
        await command.execute(token, "user", rating)
        assert len(client.rows) == 1
        row = next(iter(client.rows.values()))
        assert row["run_id"] == run_id
        assert row["key"] == "user_feedback"
        assert row["score"] == score
        assert "trace_id" not in row  # Avoid background enqueue acknowledgement.
        assert row["stop_after_attempt"] == 1
        await command.execute(token, "user", "down" if rating == "up" else "up")
        assert len(client.rows) == 1
        assert row["score"] == 1 - score
    finally:
        await adapter.aclose()
    assert client.closed


async def test_B08_concurrent_creation_conflict_is_updated():
    class RacingClient(Client):
        def create_feedback(self, **values):
            self.rows[values["feedback_id"]] = {**values, "score": -1}
            raise LangSmithConflictError("concurrent create")

    codec, client = tokens(), RacingClient()
    adapter = LangSmithFeedback(cast(SdkClient, client))
    try:
        token = codec.issue(uuid4(), "test-project", "user")
        await SubmitFeedback(tokens=codec, writer=adapter).execute(token, "user", "up")
        assert next(iter(client.rows.values()))["score"] == 1
    finally:
        await adapter.aclose()


def test_B09_B10_signed_target_identity_expiry_and_audience():
    now = [100]
    codec = tokens(lambda: now[0])
    token = codec.issue(uuid4(), "test-project", "user")
    assert codec.verify(token, "user").project_name == "test-project"
    now[0] = 100 + 86400 - 1
    codec.verify(token, "user")
    now[0] += 1
    for invalid, user in [(token, "user"), (token, "other"), ("bad", "user")]:
        with pytest.raises(FeedbackForbidden):
            codec.verify(invalid, user)
    now[0] = 100
    body, signature = token.split(".")
    with pytest.raises(FeedbackForbidden):
        codec.verify(
            body + "." + ("a" if signature[0] != "a" else "b") + signature[1:], "user"
        )
    with pytest.raises(FeedbackForbidden):
        SignedFeedbackTokens(
            secret=b"s" * 32, audience="other", clock=lambda: 100
        ).verify(token, "user")


async def test_B09_separate_answers_and_actors():
    codec, client = tokens(), Client()
    adapter = LangSmithFeedback(cast(SdkClient, client))
    command = SubmitFeedback(tokens=codec, writer=adapter)
    run = uuid4()
    try:
        for target, actor in [(run, "user"), (run, "other"), (uuid4(), "user")]:
            await command.execute(
                codec.issue(target, "test-project", actor), actor, "up"
            )
        assert len(client.rows) == 3
        with pytest.raises(FeedbackForbidden):
            await command.execute(
                codec.issue(run, "test-project", "user"), "other", "up"
            )
        assert len(client.rows) == 3
    finally:
        await adapter.aclose()


async def test_B13_failure_is_not_success():
    class BrokenClient(Client):
        def update_feedback(self, *args, **kwargs):
            raise RuntimeError("private SDK details")

    codec = tokens()
    adapter = LangSmithFeedback(cast(SdkClient, BrokenClient()))
    try:
        with pytest.raises(FeedbackUnavailable):
            await SubmitFeedback(tokens=codec, writer=adapter).execute(
                codec.issue(uuid4(), "test-project", "user"), "user", "up"
            )
    finally:
        await adapter.aclose()


async def test_B13_sdk_timeout_is_reported():
    class TimeoutClient(Client):
        def update_feedback(self, *args, **kwargs):
            raise LangSmithRequestTimeout("private details")

    codec = tokens()
    adapter = LangSmithFeedback(cast(SdkClient, TimeoutClient()))
    try:
        with pytest.raises(FeedbackTimeout):
            await SubmitFeedback(tokens=codec, writer=adapter).execute(
                codec.issue(uuid4(), "test-project", "user"), "user", "down"
            )
    finally:
        await adapter.aclose()


async def test_B06_B07_actual_sdk_uses_acknowledged_http(monkeypatch):
    import json

    from requests import Response

    client = SdkClient(
        api_key="test",
        api_url="https://test.invalid",
        auto_batch_tracing=False,
        tracing_sampling_rate=1,
        info={"version": "0.0.0"},
    )
    rows = {}
    operations = []
    project_id = uuid4()

    def request(_client, method, pathname, **kwargs):
        operations.append((method, pathname))
        if method == "PATCH":
            key = pathname.rsplit("/", 1)[1]
            if key not in rows:
                raise LangSmithNotFoundError("test missing")
            rows[key].update(json.loads(kwargs["data"]))
        elif method == "DELETE":
            key = pathname.rsplit("/", 1)[1]
            if key not in rows:
                raise LangSmithNotFoundError("test missing")
            del rows[key]
        elif method == "POST":
            row = json.loads(kwargs["request_kwargs"]["data"])
            assert row["session_id"] == str(project_id)
            assert "trace_id" not in row
            rows[row["id"]] = row
        else:
            raise AssertionError((method, pathname))
        response = Response()
        response.status_code = 200
        response._content = b"{}"
        return response

    monkeypatch.setattr(SdkClient, "request_with_retries", request)
    monkeypatch.setattr(
        SdkClient, "read_project", lambda self, **kwargs: SimpleNamespace(id=project_id)
    )
    codec = tokens()
    adapter = LangSmithFeedback(client)
    try:
        token = codec.issue(uuid4(), "test-project", "user")
        command = SubmitFeedback(tokens=codec, writer=adapter)
        await command.execute(token, "user", "up")
        await command.execute(token, "user", "up")
        await command.execute(token, "user", "down")
        assert len(rows) == 1
        assert next(iter(rows.values()))["score"] == 0
        assert [op[0] for op in operations] == ["PATCH", "POST", "PATCH", "PATCH"]
        original_id = next(iter(rows))
        await command.execute(token, "user", None)
        assert rows == {}
        await command.execute(token, "user", None)
        assert rows == {}
        await command.execute(token, "user", "up")
        assert list(rows) == [original_id]
        assert rows[original_id]["score"] == 1
    finally:
        await adapter.aclose()


async def test_B15_B16_worker_does_not_block_event_loop_and_closes():
    entered, release = threading.Event(), threading.Event()

    class SlowClient(Client):
        def update_feedback(self, *args, **kwargs):
            entered.set()
            assert release.wait(5)
            return super().update_feedback(*args, **kwargs)

    codec, client = tokens(), SlowClient()
    adapter = LangSmithFeedback(cast(SdkClient, client))
    task = asyncio.create_task(
        SubmitFeedback(tokens=codec, writer=adapter).execute(
            codec.issue(uuid4(), "test-project", "user"), "user", "up"
        )
    )
    try:
        assert await asyncio.to_thread(entered.wait, 3)
        assert not task.done()
        release.set()
        await task
    finally:
        release.set()
        await adapter.aclose()
    assert client.closed


async def test_B04_B16_optional_composition_and_sdk_ownership(monkeypatch):
    from unittest.mock import Mock

    from backend.config.feedback_settings import (
        read_feedback_settings,
    )
    from backend.infrastructure.composition import feedback_composition

    monkeypatch.delenv("MEDI_CHAT_FEEDBACK_SECRET", raising=False)
    assert read_feedback_settings() is None
    monkeypatch.setenv("MEDI_CHAT_FEEDBACK_SECRET", "s" * 31)
    assert read_feedback_settings() is None
    monkeypatch.setattr(feedback_composition, "tracing_is_enabled", lambda: True)
    monkeypatch.setattr(
        feedback_composition,
        "get_env_var",
        lambda name, default=None: "test" if name == "API_KEY" else "1",
    )
    assert feedback_composition.compose_feedback() is None
    monkeypatch.setenv("MEDI_CHAT_FEEDBACK_SECRET", "s" * 32)
    monkeypatch.setattr(feedback_composition, "tracing_is_enabled", lambda: False)
    assert feedback_composition.compose_feedback() is None
    monkeypatch.setattr(feedback_composition, "tracing_is_enabled", lambda: True)
    sdk = Mock(spec=SdkClient)
    factory = Mock(return_value=sdk)
    monkeypatch.setattr(feedback_composition, "Client", factory)
    composed = feedback_composition.compose_feedback()
    assert composed is not None
    assert factory.call_args.kwargs["auto_batch_tracing"] is False
    assert factory.call_args.kwargs["tracing_sampling_rate"] == 1
    await composed[1].aclose()
    sdk.close.assert_called_once()
