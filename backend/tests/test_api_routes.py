"""API contract tests for product resolution and document-grounded answers."""

from __future__ import annotations

import hashlib
import html
import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch
from xml.etree import ElementTree as ET

from backend.application.retrieval.intent_contracts import IntentRequest, IntentResult
from backend.domain.retrieval.primitives import IntentName, Probability
from backend.domain.retrieval.value_objects import IntentCandidate
from backend.infrastructure.persistence.index_writer import SqlAlchemyIndexWriter
from backend.infrastructure.persistence.sqlite_engine import create_sqlite_engine
from backend.infrastructure.sources.file_index_source import FileIndexSourceReader
from backend.main import create_app
from backend.tests.storage_fixtures import build_document_store
from backend.tests.test_alembic_migrations import _migrate_database
from backend.tests.test_interaction_xml_oracle import (
    ORACLE,
    assert_prompt_oracle,
    assert_public_collection,
)
from backend.tests.test_product_identity_responses import CONFIRMATIONS
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.engine import URL

REPO_ROOT = Path(__file__).resolve().parents[2]
STRUCTURED_DIR = REPO_ROOT / "data" / "pmda" / "structured"


class UnavailableIntentClassifier:
    is_available = False

    def __init__(self, **kwargs: Any) -> None:
        pass

    async def classify(self, request: IntentRequest) -> IntentResult:
        return IntentResult(is_available=False)

    async def aclose(self) -> None:
        pass


class PromptEchoProvider:
    """Observe supplied evidence deterministically; no clinical generation is claimed."""

    def __init__(self) -> None:
        self.calls: list[list[dict[str, str]]] = []

    async def stream_response(self, messages, model=None):
        self.calls.append([dict(message) for message in messages])
        yield "\n".join(message["content"] for message in messages)


class InteractionIntentClassifier:
    is_available = True

    async def classify(self, request: IntentRequest) -> IntentResult:
        return IntentResult(
            is_available=True,
            candidates=(IntentCandidate(IntentName("interaction"), Probability(1.0)),),
        )


class InteractionKeywords:
    def extract_keywords(self, text: str) -> tuple[str, ...]:
        return ("158",)


class ChatApiRouteTests(unittest.TestCase):
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
        from backend.tests.registration_runtime_fixtures import (
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
                llm_provider_factory=lambda _: PromptEchoProvider(),
                import_directory=Path(cls.temp_dir.name) / "imports",
            )
        )
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client_context.__exit__(None, None, None)
        cls.classifier_patch.stop()
        cls.temp_dir.cleanup()

    def test_health_reports_loaded_documents_and_units(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        expected_documents = list(STRUCTURED_DIR.glob("*/document.json"))
        expected_units = sum(
            sum(
                1
                for line in (document.parent / "search_units.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
                if line
            )
            for document in expected_documents
        )
        self.assertEqual(
            response.json(),
            {
                "status": "ok",
                "document_count": len(expected_documents),
                "unit_count": expected_units,
                "generation_id": self._published_generation(),
            },
        )

    def _published_generation(self) -> str:
        from contextlib import closing

        with closing(
            sqlite3.connect(self.index_path.as_uri() + "?mode=ro", uri=True)
        ) as connection:
            return connection.execute(
                "SELECT generation_id FROM registration_state WHERE singleton=1"
            ).fetchone()[0]

    def test_interaction_pair_returns_both_directions_with_row_context_and_sources(
        self,
    ) -> None:
        self._assert_interaction_xml_contract(pair=True)

    def test_single_product_interaction_query_limits_results_to_interaction_sections(
        self,
    ) -> None:
        self._assert_interaction_xml_contract(pair=False)

    def _assert_interaction_xml_contract(self, *, pair: bool) -> None:
        documents = ORACLE if pair else ORACLE[:1]
        question = (
            "イグザレルト錠2.5mgとイトラコナゾールの飲み合わせを教えて"
            if pair
            else "イグザレルト錠2.5mgの飲み合わせ"
        )
        provider = PromptEchoProvider()
        application = self.client.app
        assert isinstance(application, FastAPI)
        service = application.state.chat_service
        with (
            patch.object(service, "intent_classifier", InteractionIntentClassifier()),
            patch.object(service, "keyword_extractor", InteractionKeywords()),
            patch.object(service, "provider_factory", lambda _: provider),
        ):
            response = self.client.post(
                "/api/chat",
                json={
                    "message": question,
                    "product_yj_codes": [doc["yj"] for doc in documents],
                },
            )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["intent"], "interaction")
        self.assertEqual(payload["retrieval_strategy"], "three_detectors")
        self.assertFalse(payload["needs_clarification"])
        assert_public_collection(payload["sources"], pair)
        expected_groups = {
            name: {
                "generic_name": name,
                "brand_names": [
                    doc["product_name"]
                    for doc in documents
                    if doc["generic_name"] == name
                ],
                "yj_codes": [
                    doc["yj"] for doc in documents if doc["generic_name"] == name
                ],
                "document_ids": [
                    doc["document_id"]
                    for doc in documents
                    if doc["generic_name"] == name
                ],
                "matched_aliases": [],
            }
            for name in {doc["generic_name"] for doc in documents}
        }

        def normalize(group):
            return {
                key: sorted(value) if isinstance(value, list) else value
                for key, value in group.items()
            }

        self.assertEqual(
            {
                group["generic_name"]: normalize(group)
                for group in payload["resolved_medicines"]
            },
            {name: normalize(group) for name, group in expected_groups.items()},
        )
        self.assertEqual(len(provider.calls), 1)
        assert_prompt_oracle(provider.calls[0], documents, history=False)
        self.assertEqual(
            payload["answer"],
            "\n".join(message["content"] for message in provider.calls[0]),
        )
        self.assertIn("10.1 併用禁忌", payload["answer"])
        self.assertIn("10.2 併用注意", payload["answer"])

    def test_unmatched_counterpart_does_not_claim_combination_is_safe(self) -> None:
        response = self.client.post(
            "/api/chat",
            json={
                "message": "イグザレルト錠2.5mgと未知薬の併用は可能ですか",
                "product_yj_codes": ["3339003F5020"],
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["needs_clarification"])
        self.assertEqual(payload["sources"], [])
        self.assertNotIn("併用可能です", payload["answer"])
        self.assertEqual(payload["retrieval_strategy"], "unresolved_counterpart")
        self.assertEqual(payload["answer"], CONFIRMATIONS["unresolved_counterpart"][0])
        self.assertEqual(
            payload["notices"], [CONFIRMATIONS["unresolved_counterpart"][1]]
        )
        self.assertEqual(payload["resolved_medicines"][0]["yj_codes"], ["3339003F5020"])

    def test_adverse_event_question_filters_to_adverse_event_sections(self) -> None:
        response = self.client.post(
            "/api/chat",
            json={
                "message": "イグザレルト錠2.5mgの副作用を教えて",
                "product_yj_codes": ["3339003F5020"],
                "max_sources": 6,
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["intent"], "adverse_events")
        raw_source = next((REPO_ROOT / "data/pmda/originals").glob("*/*630004*.xml"))
        raw_root = ET.parse(raw_source).getroot()
        expected_sha = hashlib.sha256(raw_source.read_bytes()).hexdigest()
        adverse = next(
            node
            for node in raw_root.iter()
            if node.tag.rsplit("}", 1)[-1] == "AdverseEvents"
        )
        raw_leaf_texts = [
            node.text
            for node in adverse.iter()
            if node.tag.rsplit("}", 1)[-1] == "Lang"
            and not len(node)
            and node.text
            and node.text.strip()
        ]
        supplied_body = "".join(
            html.unescape(
                "\n".join(source["excerpt"] for source in payload["sources"])
            ).split()
        )
        self.assertTrue(raw_leaf_texts)
        for original_text in raw_leaf_texts:
            self.assertIn("".join(original_text.split()), supplied_body)
        self.assertEqual(
            {source["unit_id"] for source in payload["sources"]},
            {
                f"630004_3339003F5020_1_08:{expected_sha}:11",
                f"630004_3339003F5020_1_08:{expected_sha}:11.1",
                f"630004_3339003F5020_1_08:{expected_sha}:11.2",
            },
        )
        self.assertEqual(len(payload["sources"]), 3)
        self.assertTrue(
            all(
                source["section"]["code"].startswith("11")
                for source in payload["sources"]
            )
        )

    def test_reproductive_potential_question_filters_to_section_9_4(self) -> None:
        response = self.client.post(
            "/api/chat",
            json={
                "message": "妊娠可能な女性の避妊方法を教えて",
                "product_yj_codes": ["6290004M1029"],
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["intent"], "reproductive_potential")
        self.assertTrue(payload["sources"])
        self.assertTrue(
            all(source["section"]["code"] == "9.4" for source in payload["sources"])
        )
        self.assertTrue(
            any(
                "最終投与後1ヵ月間" in source["excerpt"]
                for source in payload["sources"]
            )
        )

    def test_pregnancy_question_filters_to_section_9_5(self) -> None:
        response = self.client.post(
            "/api/chat",
            json={
                "message": "妊娠中の注意点を教えて",
                "product_yj_codes": ["6290004M1029"],
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["intent"], "pregnancy")
        self.assertTrue(payload["sources"])
        self.assertTrue(
            all(source["section"]["code"] == "9.5" for source in payload["sources"])
        )

    def test_invalid_message_length_is_rejected(self) -> None:
        codes = ["3339003F5020"]
        empty = self.client.post(
            "/api/chat", json={"message": "", "product_yj_codes": codes}
        )
        whitespace = self.client.post(
            "/api/chat", json={"message": "   ", "product_yj_codes": codes}
        )
        too_long = self.client.post(
            "/api/chat",
            json={"message": "薬" * 2001, "product_yj_codes": codes},
        )

        self.assertEqual(empty.status_code, 422)
        self.assertEqual(whitespace.status_code, 422)
        self.assertEqual(too_long.status_code, 422)

    def test_chat_requires_at_least_one_yj_code(self) -> None:
        missing = self.client.post("/api/chat", json={"message": "副作用を教えて"})
        empty = self.client.post(
            "/api/chat",
            json={"message": "副作用を教えて", "product_yj_codes": []},
        )

        self.assertEqual(missing.status_code, 422)
        self.assertEqual(empty.status_code, 422)

    def test_chat_rejects_malformed_yj_code(self) -> None:
        response = self.client.post(
            "/api/chat",
            json={"message": "副作用を教えて", "product_yj_codes": ["3339003"]},
        )

        self.assertEqual(response.status_code, 422)

    def test_chat_rejects_duplicate_yj_codes(self) -> None:
        response = self.client.post(
            "/api/chat",
            json={
                "message": "副作用を教えて",
                "product_yj_codes": ["3339003F5020", "3339003F5020"],
            },
        )

        self.assertEqual(response.status_code, 422)

    def test_unknown_well_formed_yj_code_requests_clarification(self) -> None:
        response = self.client.post(
            "/api/chat",
            json={"message": "副作用を教えて", "product_yj_codes": ["0000000A0000"]},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["needs_clarification"])
        self.assertEqual(payload["resolved_medicines"], [])
        self.assertEqual(payload["sources"], [])

    def test_unknown_yj_code_prevents_partial_answer_for_multiple_products(
        self,
    ) -> None:
        response = self.client.post(
            "/api/chat",
            json={
                "message": "副作用を教えて",
                "product_yj_codes": ["3339003F5020", "0000000A0000"],
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["needs_clarification"])
        self.assertEqual(len(payload["resolved_medicines"]), 1)
        self.assertEqual(payload["resolved_medicines"][0]["yj_codes"], ["3339003F5020"])
        self.assertEqual(
            payload["resolved_medicines"][0]["document_ids"],
            ["630004_3339003F5020_1_08"],
        )
        self.assertEqual(payload["sources"], [])

    def test_pair_interaction_requires_yj_code_for_each_product(self) -> None:
        response = self.client.post(
            "/api/chat",
            json={
                "message": "イグザレルト錠2.5mgとイトラコナゾールの飲み合わせ",
                "product_yj_codes": ["3339003F5020"],
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["needs_clarification"])
        self.assertEqual(payload["retrieval_strategy"], "pair_yj_codes_required")
        self.assertEqual(payload["sources"], [])
        self.assertEqual(payload["answer"], CONFIRMATIONS["pair_yj_codes_required"][0])
        self.assertEqual(
            payload["notices"], [CONFIRMATIONS["pair_yj_codes_required"][1]]
        )
        self.assertEqual(payload["resolved_medicines"][0]["yj_codes"], ["3339003F5020"])
        self._assert_interaction_xml_contract(pair=True)

    def test_chat_uses_yj_code_as_product_identity(self) -> None:
        response = self.client.post(
            "/api/chat",
            json={
                "message": "この薬の副作用を教えて",
                "product_yj_codes": ["3339003F5020"],
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["resolved_medicines"][0]["yj_codes"], ["3339003F5020"])
        self.assertTrue(payload["sources"])
        self.assertEqual(
            {source["document_id"] for source in payload["sources"]},
            {"630004_3339003F5020_1_08"},
        )

    def test_empty_document_store_fails_at_startup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = create_app(
                Path(temp_dir) / "missing", Path(temp_dir) / "index.sqlite3"
            )
            with self.assertRaises(RuntimeError), TestClient(app):
                pass

    def test_adding_a_structured_document_refreshes_the_sqlite_index(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            structured_dir = root / "structured"
            structured_dir.mkdir()
            first_source = STRUCTURED_DIR / "630004_3339003F5020_1_08"
            second_source = STRUCTURED_DIR / "800155_6290004M1029_1_47"
            shutil.copytree(first_source, structured_dir / first_source.name)

            first_document_store = build_document_store(
                structured_dir, root / "index.sqlite3"
            )
            first_stats = first_document_store.index_stats
            shutil.copytree(second_source, structured_dir / second_source.name)

            refreshed_document_store = build_document_store(
                structured_dir, root / "index.sqlite3"
            )

            self.assertEqual(
                refreshed_document_store.index_stats["document_count"],
                first_stats["document_count"] + 1,
            )
            self.assertGreater(
                refreshed_document_store.index_stats["unit_count"],
                first_stats["unit_count"],
            )

    def test_medicine_lookup_resolves_brand_and_yj_code(self) -> None:
        response = self.client.get("/api/medicines", params={"query": "イグザレルト"})

        self.assertEqual(response.status_code, 200)
        items = response.json()["items"]
        self.assertEqual(len(items), 1)
        self.assertIn("3339003F5020", items[0]["yj_codes"])

    def test_medicine_catalog_reads_all_products_from_structured_documents(
        self,
    ) -> None:
        response = self.client.get("/api/medicines")

        self.assertEqual(response.status_code, 200)
        items = response.json()["items"]
        expected_codes = {
            product["yj_code"]
            for document_path in STRUCTURED_DIR.glob("*/document.json")
            for product in json.loads(document_path.read_text(encoding="utf-8"))[
                "document"
            ]["products"]
        }
        actual_codes = {code for item in items for code in item["yj_codes"]}
        self.assertEqual(actual_codes, expected_codes)

    def test_specific_generic_product_name_disambiguates_same_ingredient(self) -> None:
        response = self.client.get(
            "/api/medicines",
            params={"query": "イトラコナゾールカプセル50mg「SW」"},
        )

        self.assertEqual(response.status_code, 200)
        items = response.json()["items"]
        self.assertEqual(len(items), 1)

    def test_contraindication_query_returns_section_2_not_interaction_10_1(
        self,
    ) -> None:
        response = self.client.post(
            "/api/chat",
            json={
                "message": "イグザレルト錠2.5mgの禁忌を教えて",
                "product_yj_codes": ["3339003F5020"],
                "max_sources": 3,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["intent"], "contraindications")
        self.assertTrue(len(payload["sources"]) > 0)
        self.assertTrue(
            all(source["section"]["code"] == "2" for source in payload["sources"])
        )

    def test_storage_query_returns_section_20_not_appearance_3_2(self) -> None:
        # Itraconazole has section 20
        response = self.client.post(
            "/api/chat",
            json={
                "message": "イトリゾールカプセル50の保存方法を教えて",
                "product_yj_codes": ["6290004M1029"],
                "max_sources": 3,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["intent"], "storage_and_handling")
        self.assertTrue(len(payload["sources"]) > 0)
        self.assertTrue(
            all(source["section"]["code"] == "20" for source in payload["sources"])
        )

        # Xarelto does NOT have section 20; must not erroneously return section 3.2 (appearance)
        response_xarelto = self.client.post(
            "/api/chat",
            json={
                "message": "イグザレルト錠2.5mgの保存方法を教えて",
                "product_yj_codes": ["3339003F5020"],
                "max_sources": 3,
            },
        )
        self.assertEqual(response_xarelto.status_code, 200)
        payload_x = response_xarelto.json()
        self.assertEqual(payload_x["intent"], "storage_and_handling")
        self.assertFalse(
            any(source["section"]["code"] == "3.2" for source in payload_x["sources"])
        )

    def test_appearance_query_returns_section_3_2(self) -> None:
        response = self.client.post(
            "/api/chat",
            json={
                "message": "イグザレルト錠2.5mgの性状や剤形を教えて",
                "product_yj_codes": ["3339003F5020"],
                "max_sources": 3,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["intent"], "appearance")
        self.assertTrue(len(payload["sources"]) > 0)
        self.assertTrue(
            all(source["section"]["code"] == "3.2" for source in payload["sources"])
        )

    def test_amaryl_indications_resolved_and_returns_section_4(self) -> None:
        response = self.client.post(
            "/api/chat",
            json={
                "message": "アマリールの効果を教えて",
                "product_yj_codes": ["3961008F1020"],
                "max_sources": 3,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["intent"], "indications")
        self.assertGreater(len(payload["sources"]), 0)
        first_source = payload["sources"][0]
        self.assertEqual(first_source["section"]["code"], "4")
        self.assertIn("2型糖尿病", first_source["excerpt"])

    def test_amaryl_indications_natural_phrasing(self) -> None:
        response = self.client.post(
            "/api/chat",
            json={
                "message": "アマリールは何に効く？",
                "product_yj_codes": ["3961008F1020"],
                "max_sources": 3,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["intent"], "indications")
        self.assertGreater(len(payload["sources"]), 0)
        self.assertEqual(payload["sources"][0]["section"]["code"], "4")

    def test_amaryl_brand_name_lookup_and_override_mismatched_yj(self) -> None:
        # 1. Verify /api/medicines resolves "アマリール"
        lookup = self.client.get("/api/medicines", params={"query": "アマリール"})
        self.assertEqual(lookup.status_code, 200)
        items = lookup.json()["items"]
        self.assertEqual(len(items), 1)
        self.assertIn("3961008F1020", items[0]["yj_codes"])

        # 2. A direct name conflict keeps the explicitly selected Xarelto chip.
        response = self.client.post(
            "/api/chat",
            json={
                "message": "アマリールの効能は？",
                "product_yj_codes": ["3339003F5020"],
                "max_sources": 3,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["intent"], "indications")
        self.assertEqual(payload["retrieval_strategy"], "product_identity_conflict")
        self.assertTrue(payload["needs_clarification"])
        self.assertEqual(payload["sources"], [])
        self.assertEqual(
            payload["answer"], CONFIRMATIONS["product_identity_conflict"][0]
        )
        self.assertEqual(
            payload["notices"], [CONFIRMATIONS["product_identity_conflict"][1]]
        )
        self.assertEqual(payload["resolved_medicines"][0]["yj_codes"], ["3339003F5020"])
        self.assertEqual(
            payload["resolved_medicines"][0]["generic_name"], "リバーロキサバン"
        )

        # 3. Correct Amaryl selection preserves the original indication oracle.
        correct = self.client.post(
            "/api/chat",
            json={
                "message": "アマリールの効能は？",
                "product_yj_codes": ["3961008F1020"],
            },
        )
        self.assertEqual(correct.status_code, 200)
        payload = correct.json()
        self.assertEqual(payload["intent"], "indications")
        self.assertFalse(payload["needs_clarification"])
        self.assertEqual(payload["retrieval_strategy"], "three_detectors")
        self.assertGreater(len(payload["sources"]), 0)
        self.assertEqual(payload["sources"][0]["section"]["code"], "4")
        self.assertIn("2型糖尿病", payload["sources"][0]["excerpt"])
        self.assertEqual(
            payload["resolved_medicines"][0]["generic_name"], "グリメピリド"
        )
        self.assertEqual(payload["resolved_medicines"][0]["yj_codes"], ["3961008F1020"])

    def test_xarelto_indications_has_scope_and_not_bare_adult_heading(self) -> None:
        response = self.client.post(
            "/api/chat",
            json={
                "message": "イグザレルトの効能効果は？",
                "product_yj_codes": ["3339003F5020"],
                "max_sources": 3,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["intent"], "indications")
        self.assertGreater(len(payload["sources"]), 0)
        excerpts = [s["excerpt"] for s in payload["sources"]]
        self.assertNotIn("成人", excerpts)
        self.assertNotIn("小児", excerpts)
        self.assertTrue(
            any(
                "〈成人〉" in e
                and "下肢血行再建術施行後の末梢動脈疾患患者における血栓・塞栓形成の抑制"
                in e
                for e in excerpts
            )
        )
        self.assertTrue(
            any(
                "〈小児〉" in e and "Fontan手術施行後における血栓・塞栓形成の抑制" in e
                for e in excerpts
            )
        )

    def test_interaction_pair_without_direct_rows_falls_back_to_product_interaction_sections(
        self,
    ) -> None:
        # Xarelto (3339003F5020) and Olmesartan (2149044F4139) have no mutual direct interaction rows,
        # but both have interaction sections (10, 10.1, 10.2, 16.7).
        response = self.client.post(
            "/api/chat",
            json={
                "message": "飲み合わせは？",
                "product_yj_codes": ["3339003F5020", "2149044F4139"],
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["intent"], "interaction")
        self.assertGreater(len(payload["sources"]), 0)
        # Verify both products are present in the retrieved sources
        doc_keys = {s["document_id"] for s in payload["sources"]}
        self.assertIn("630004_3339003F5020_1_08", doc_keys)
        self.assertIn("530169_2149044F1121_1_06", doc_keys)
        # All sources belong to interaction sections
        self.assertTrue(
            all(
                s["section"]["code"] in {"10", "10.1", "10.2", "16.7"}
                for s in payload["sources"]
            )
        )
        # Answer conveys that direct mutual rows were not found, but interaction sections were retrieved
        self.assertIn("互いを直接指定する", payload["answer"])


if __name__ == "__main__":
    unittest.main()
