"""Tests that clarification replies do not invoke an LLM provider."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from backend.main import create_app
from backend.tests.support.paths import PROJECT_ROOT
from fastapi.testclient import TestClient

REPO_ROOT = PROJECT_ROOT
STRUCTURED_DIR = REPO_ROOT / "data" / "pmda" / "structured"


class RecordingLLMProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[list[dict[str, str]], str | None]] = []

    async def stream_response(
        self, messages: list[dict[str, str]], model: str | None = None
    ) -> Any:
        self.calls.append((messages, model))
        yield "LLM_SHOULD_NOT_RUN"


class ClarificationResponseTests(unittest.TestCase):
    temp_dir: tempfile.TemporaryDirectory[str]
    index_path: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.index_path = Path(cls.temp_dir.name) / "chat-search.sqlite3"
        from backend.tests.support.registration_runtime_fixtures import (
            register_existing_test_source,
        )

        cls.prepared_source = register_existing_test_source(
            STRUCTURED_DIR, cls.index_path
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_dir.cleanup()

    def test_rest_clarification_does_not_call_provider(self) -> None:
        provider = RecordingLLMProvider()
        app = create_app(
            self.prepared_source,
            self.index_path,
            llm_provider_factory=lambda _name: provider,
            import_directory=Path(self.temp_dir.name) / "imports",
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
        app = create_app(
            self.prepared_source,
            self.index_path,
            llm_provider_factory=lambda _name: provider,
            import_directory=Path(self.temp_dir.name) / "imports",
        )
        with (
            TestClient(app) as client,
            client.websocket_connect("/ws/chat") as websocket,
        ):
            websocket.send_json(
                {
                    "type": "message",
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
