"""WR-023: cancelling a request must preserve the application-owned Jev client."""

import asyncio

import pytest
from backend.application.retrieval.queries.models import IntentRequest
from backend.infrastructure.intent import jev_classifier
from backend.tests.integration.test_sdk_lifecycle import LifecycleTypeSafeClient


@pytest.mark.asyncio
async def test_WR023_cancel_then_reuse_shared_jev_client(monkeypatch):
    client = LifecycleTypeSafeClient("cancel")
    monkeypatch.setattr(
        jev_classifier.ts, "AsyncTypeSafeClient", lambda **kwargs: client
    )
    classifier = jev_classifier.JevIntentClassifier(api_key="test-key")
    task = asyncio.create_task(classifier.classify(IntentRequest("テスト質問A")))
    try:
        await asyncio.wait_for(client.started.wait(), 1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert client.active == 0
        assert classifier._active_calls == 0
        assert client.closed == 0
        client.path = "normal"
        result = await classifier.classify(IntentRequest("テスト質問B"))
        assert result.is_available
        assert client.calls == client.finished == 2
        assert client.closed == 0
    finally:
        client.release.set()
        if not task.done():
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        await classifier.aclose()
    assert client.closed == 1
