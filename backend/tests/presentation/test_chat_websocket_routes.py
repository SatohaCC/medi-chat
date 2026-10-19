"""Tests for WebSocket chat streaming endpoint."""

from __future__ import annotations

import os
import unittest
from typing import Any
from unittest.mock import patch

from backend.tests.support.postgres_public_application import (
    original_application_factory,
)
from fastapi.testclient import TestClient


class ChatWebSocketRouteTests(unittest.TestCase):
    app: Any
    client_context: Any
    client: TestClient

    @classmethod
    def setUpClass(cls) -> None:
        cls.database_context = original_application_factory()
        build = cls.database_context.__enter__()
        cls.app = build()
        cls.client_context = TestClient(cls.app)
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client_context.__exit__(None, None, None)
        cls.database_context.__exit__(None, None, None)

    def test_api_health(self) -> None:
        response = self.client.get("/api")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_websocket_ping_pong(self) -> None:
        with self.client.websocket_connect("/api/ws") as websocket:
            websocket.send_json({"type": "ping"})
            data = websocket.receive_json()
            self.assertEqual(data["type"], "pong")

    def test_websocket_chat_streaming_gemini_fallback(self) -> None:
        with (
            patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}),
            self.client.websocket_connect("/ws/chat") as websocket,
        ):
            websocket.send_json(
                {
                    "type": "message",
                    "provider": "gemini",
                    "product_yj_codes": ["3339003F5020"],
                    "messages": [{"role": "user", "content": "こんにちは"}],
                }
            )
            deltas: list[str] = []
            while True:
                data = websocket.receive_json()
                if data["type"] == "sources":
                    continue
                if data["type"] == "text_delta":
                    deltas.append(data["content"])
                elif data["type"] == "text_done":
                    break
                elif data["type"] == "error":
                    self.fail(f"Unexpected error: {data['content']}")
            full_response = "".join(deltas)
            self.assertIn("Gemini", full_response)
            self.assertIn("こんにちは", full_response)

    def test_websocket_chat_streaming_openai_fallback(self) -> None:
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": ""}),
            self.client.websocket_connect("/ws/chat") as websocket,
        ):
            websocket.send_json(
                {
                    "type": "message",
                    "provider": "openai",
                    "product_yj_codes": ["3339003F5020"],
                    "messages": [{"role": "user", "content": "おはよう"}],
                }
            )
            deltas: list[str] = []
            while True:
                data = websocket.receive_json()
                if data["type"] == "sources":
                    continue
                if data["type"] == "text_delta":
                    deltas.append(data["content"])
                elif data["type"] == "text_done":
                    break
                elif data["type"] == "error":
                    self.fail(f"Unexpected error: {data['content']}")
            full_response = "".join(deltas)
            self.assertIn("OpenAI", full_response)
            self.assertIn("おはよう", full_response)

    def test_websocket_chat_sends_sources_for_medical_question(self) -> None:
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": ""}),
            self.client.websocket_connect("/ws/chat") as websocket,
        ):
            websocket.send_json(
                {
                    "type": "message",
                    "provider": "openai",
                    "product_yj_codes": ["3339003F5020"],
                    "messages": [
                        {"role": "user", "content": "イグザレルトの禁忌を教えて"}
                    ],
                }
            )
            received_sources: list[dict[str, Any]] = []
            deltas: list[str] = []
            while True:
                data = websocket.receive_json()
                if data["type"] == "sources":
                    received_sources = data["sources"]
                elif data["type"] == "text_delta":
                    deltas.append(data["content"])
                elif data["type"] == "text_done":
                    break
                elif data["type"] == "error":
                    self.fail(f"Unexpected error: {data['content']}")
            self.assertTrue(len(received_sources) > 0)
            full_response = "".join(deltas)
            self.assertIn("根拠", full_response)

    def test_websocket_chat_sends_jev_response(self) -> None:
        from unittest.mock import AsyncMock, MagicMock

        mock_jev = MagicMock()
        mock_jev.is_available = True
        mock_payload = {
            "model": "jev-mock-1",
            "answers": {
                "intent": {
                    "type": "choice",
                    "choice": "dosage",
                    "confidence": 0.92,
                    "probabilities": {"dosage": 0.92, "other": 0.08},
                }
            },
        }
        from backend.infrastructure.intent.jev_intent_mapping import (
            map_jev_intent_result,
        )

        mock_jev.classify = AsyncMock(return_value=map_jev_intent_result(mock_payload))

        with (
            patch.object(self.app.state.chat_service, "intent_classifier", mock_jev),
            patch.dict(os.environ, {"OPENAI_API_KEY": ""}),
            self.client.websocket_connect("/ws/chat") as websocket,
        ):
            websocket.send_json(
                {
                    "type": "message",
                    "provider": "openai",
                    "product_yj_codes": ["3339003F5020"],
                    "messages": [{"role": "user", "content": "1日何回飲む？"}],
                }
            )
            received_jev_response: dict[str, Any] | None = None
            received_status_response: dict[str, Any] | None = None
            while True:
                data = websocket.receive_json()
                if data["type"] == "jev_response":
                    received_jev_response = data["data"]
                elif (
                    data["type"] == "retrieval_status"
                    and data.get("stage") == "complete"
                ):
                    received_status_response = data.get("jev_response")
                elif data["type"] == "text_done":
                    break
                elif data["type"] == "error":
                    self.fail(f"Unexpected error: {data['content']}")

            self.assertIsNotNone(received_jev_response)
            assert received_jev_response is not None
            self.assertEqual(received_jev_response["model"], "jev-mock-1")
            self.assertEqual(
                received_jev_response["answers"]["intent"]["choice"], "dosage"
            )
            self.assertEqual(received_status_response, received_jev_response)

    def test_websocket_chat_sends_evidence_without_generated_ui(self) -> None:
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": ""}),
            self.client.websocket_connect("/ws/chat") as websocket,
        ):
            websocket.send_json(
                {
                    "type": "message",
                    "provider": "openai",
                    "product_yj_codes": ["3339003F5020"],
                    "messages": [
                        {
                            "role": "user",
                            "content": "イグザレルトの併用禁忌について教えて",
                        }
                    ],
                }
            )
            received_sources = []
            while True:
                data = websocket.receive_json()
                self.assertNotEqual(data["type"], "genui_spec")
                if data["type"] == "sources":
                    received_sources = data["sources"]
                elif data["type"] == "text_done":
                    break
                elif data["type"] == "error":
                    self.fail(f"Unexpected error: {data['content']}")
            self.assertTrue(received_sources)
            self.assertTrue(all("excerpt" in source for source in received_sources))

    def test_websocket_chat_missing_yj_codes_returns_error(self) -> None:
        with self.client.websocket_connect("/ws/chat") as websocket:
            websocket.send_json(
                {
                    "type": "message",
                    "messages": [{"role": "user", "content": "こんにちは"}],
                }
            )
            data = websocket.receive_json()
            self.assertEqual(data["type"], "error")
            self.assertIn("product_yj_codes", data["content"])

    def test_websocket_chat_empty_messages_returns_error(self) -> None:
        with self.client.websocket_connect("/ws/chat") as websocket:
            websocket.send_json(
                {
                    "type": "message",
                    "product_yj_codes": ["3339003F5020"],
                    "messages": [],
                }
            )
            data = websocket.receive_json()
            self.assertEqual(data["type"], "error")

    def test_websocket_chat_invalid_model_returns_error(self) -> None:
        with self.client.websocket_connect("/ws/chat") as websocket:
            websocket.send_json(
                {
                    "type": "message",
                    "provider": "openai",
                    "model": "unsupported-model-x",
                    "product_yj_codes": ["3339003F5020"],
                    "messages": [{"role": "user", "content": "こんにちは"}],
                }
            )
            data = websocket.receive_json()
            self.assertEqual(data["type"], "error")
            self.assertIn("Unsupported model", data["content"])

    def test_websocket_rejects_unauthorized_origin(self) -> None:
        from starlette.websockets import WebSocketDisconnect

        with (
            self.assertRaises(WebSocketDisconnect) as cm,
            self.client.websocket_connect(
                "/ws/chat", headers={"origin": "http://malicious-site.example.com"}
            ),
        ):
            pass
        self.assertEqual(cm.exception.code, 1008)


if __name__ == "__main__":
    unittest.main()
