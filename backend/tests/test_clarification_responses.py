"""Tests that clarification replies do not invoke an LLM provider."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from backend.infrastructure.persistence.index_writer import SqlAlchemyIndexWriter
from backend.infrastructure.persistence.sqlite_engine import create_sqlite_engine
from backend.infrastructure.sources.file_index_source import FileIndexSourceReader
from backend.main import create_app
from backend.tests.test_alembic_migrations import _migrate_database
from fastapi.testclient import TestClient
from sqlalchemy.engine import URL

REPO_ROOT = Path(__file__).resolve().parents[2]
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
        _migrate_database(cls.index_path, STRUCTURED_DIR)
        engine = create_sqlite_engine(
            URL.create("sqlite", database=cls.index_path.as_posix()).render_as_string(
                hide_password=False
            )
        )
        try:
            SqlAlchemyIndexWriter(engine).replace(
                FileIndexSourceReader(STRUCTURED_DIR).read_snapshot()
            )
        finally:
            engine.dispose()
        from backend.tests.registration_runtime_fixtures import (
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
