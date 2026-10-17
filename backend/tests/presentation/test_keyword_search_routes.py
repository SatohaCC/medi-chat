"""API contract tests for package insert keyword search endpoint."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from backend.application.retrieval.intent_contracts import IntentRequest, IntentResult
from backend.infrastructure.persistence.index_writer import SqlAlchemyIndexWriter
from backend.infrastructure.persistence.sqlite_engine import create_sqlite_engine
from backend.infrastructure.sources.file_index_source import FileIndexSourceReader
from backend.main import create_app
from backend.tests.infrastructure.persistence.test_alembic_migrations import (
    _migrate_database,
)
from backend.tests.support.paths import PROJECT_ROOT
from fastapi.testclient import TestClient
from sqlalchemy.engine import URL

REPO_ROOT = PROJECT_ROOT
STRUCTURED_DIR = REPO_ROOT / "data" / "pmda" / "structured"


class UnavailableIntentClassifier:
    is_available = False

    def __init__(self, **kwargs: Any) -> None:
        pass

    async def classify(self, request: IntentRequest) -> IntentResult:
        return IntentResult(is_available=False)

    async def aclose(self) -> None:
        pass


class KeywordSearchApiRouteTests(unittest.TestCase):
    temp_dir: tempfile.TemporaryDirectory[str]
    index_path: Path
    client_context: Any
    client: TestClient
    classifier_patch: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        index_path = Path(cls.temp_dir.name) / "chat-search.sqlite3"
        cls.index_path = index_path
        _migrate_database(index_path, STRUCTURED_DIR)
        engine = create_sqlite_engine(
            URL.create("sqlite", database=index_path.as_posix()).render_as_string(
                hide_password=False
            )
        )
        try:
            SqlAlchemyIndexWriter(engine).replace(
                FileIndexSourceReader(STRUCTURED_DIR).read_snapshot()
            )
        finally:
            engine.dispose()
        from backend.tests.support.registration_runtime_fixtures import (
            register_existing_test_source,
        )

        prepared = register_existing_test_source(STRUCTURED_DIR, index_path)
        cls.classifier_patch = patch(
            "backend.main.JevIntentClassifier", UnavailableIntentClassifier
        )
        cls.classifier_patch.start()
        cls.client_context = TestClient(
            create_app(
                prepared,
                index_path,
                import_directory=Path(cls.temp_dir.name) / "imports",
            )
        )
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client_context.__exit__(None, None, None)
        cls.classifier_patch.stop()
        cls.temp_dir.cleanup()

    def test_search_without_yj_codes_searches_all_registered_medicines(self) -> None:
        response = self.client.get("/api/search", params={"q": "副作用"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["query"], "副作用")
        self.assertGreater(data["total_count"], 0)
        self.assertEqual(len(data["items"]), data["total_count"])
        # Ensure returned items have expected fields
        first = data["items"][0]
        self.assertIn("unit_id", first)
        self.assertIn("product_name", first)
        self.assertIn("section", first)
        self.assertIn("excerpt", first)
        self.assertIn("retrieved_by", first)
        self.assertIn("keyword", first["retrieved_by"])

    def test_search_with_yj_codes_filters_to_specified_medicine(self) -> None:
        # Xarelto YJ code: 3339003F5020
        response_all = self.client.get("/api/search", params={"q": "副作用"})
        response_xarelto = self.client.get(
            "/api/search",
            params={"q": "副作用", "yj_codes": ["3339003F5020"]},
        )
        self.assertEqual(response_xarelto.status_code, 200)
        data_all = response_all.json()
        data_xarelto = response_xarelto.json()
        self.assertGreater(data_xarelto["total_count"], 0)
        self.assertLessEqual(data_xarelto["total_count"], data_all["total_count"])
        # Verify that all results belong to Xarelto
        for item in data_xarelto["items"]:
            self.assertIn("3339003F5020", item["product_yj_codes"])

    def test_search_with_nonexistent_keyword_returns_empty(self) -> None:
        response = self.client.get(
            "/api/search", params={"q": "存在しない謎の単語12345XYZ"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_count"], 0)
        self.assertEqual(data["items"], [])

    def test_search_with_single_character_returns_empty_safely(self) -> None:
        response = self.client.get("/api/search", params={"q": "あ"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_count"], 0)
        self.assertEqual(data["items"], [])

    def test_search_with_empty_query_is_rejected(self) -> None:
        response = self.client.get("/api/search", params={"q": ""})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
