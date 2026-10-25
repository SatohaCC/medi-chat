"""Tests that clarification replies do not invoke an LLM provider."""

from __future__ import annotations

import unittest
from typing import Any

import pytest
from backend.tests.support.postgres_public_application import (
    original_application_factory,
)
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.postgres, pytest.mark.source_data]


class RecordingLLMProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[list[dict[str, str]], str | None]] = []

    async def stream_response(
        self, messages: list[dict[str, str]], model: str | None = None
    ) -> Any:
        self.calls.append((messages, model))
        yield "LLM_SHOULD_NOT_RUN"


class ClarificationResponseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.database_context = original_application_factory()
        cls.build = staticmethod(cls.database_context.__enter__())

    @classmethod
    def tearDownClass(cls) -> None:
        cls.database_context.__exit__(None, None, None)

    def test_rest_clarification_does_not_call_provider(self) -> None:
        provider = RecordingLLMProvider()
        app = self.build(
            llm_provider_factory=lambda _name: provider,
        )
        with TestClient(app) as client:
            response = client.post(
                "/api/chat",
                json={
                    "message": "副作用を教えて",
                    "product_yj_codes": ["0000000A0000"],
                    "generate_llm": True,
                    "provider": "openai",
                    "model": "gpt-6-luna",
                },
            )

        payload = response.json()
        self.assertTrue(payload["needs_clarification"])
        self.assertEqual(provider.calls, [])
        self.assertIn("YJコード", payload["answer"])
        self.assertNotEqual(payload["answer"], "LLM_SHOULD_NOT_RUN")

    def test_websocket_clarification_does_not_call_provider(self) -> None:
        provider = RecordingLLMProvider()
        app = self.build(
            llm_provider_factory=lambda _name: provider,
        )
        with (
            TestClient(app) as client,
            client.websocket_connect("/ws/chat") as websocket,
        ):
            websocket.send_json(
                {
                    "type": "message",
                    "request_id": "a871f25a-1eb7-4c5e-8c6e-4511dce60280",
                    "product_yj_codes": ["0000000A0000"],
                    "messages": [{"role": "user", "content": "副作用を教えて"}],
                }
            )
            events = []
            while not events or events[-1]["type"] != "text_done":
                events.append(websocket.receive_json())

        self.assertEqual(
            [event["type"] for event in events],
            ["retrieval_status", "text_delta", "text_done"],
        )
        self.assertIn("YJコード", events[1]["content"])
        self.assertEqual(provider.calls, [])


if __name__ == "__main__":
    unittest.main()
