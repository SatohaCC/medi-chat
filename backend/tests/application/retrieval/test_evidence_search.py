"""正本の検出完了と検索開始の順序を検証する。"""

import asyncio
import unittest
from unittest.mock import patch

from backend.application.medicine.product_models import RegisteredMedicine
from backend.application.retrieval.intent_contracts import IntentRequest, IntentResult
from backend.application.retrieval.retrieve_evidence import (
    collect_search_criteria,
    retrieve_evidence,
)
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.attachment.primitives import PmdaUrl
from backend.domain.attachment.value_objects import (
    AttachmentProductRevision,
    MedicineDocumentReference,
)
from backend.domain.medicine.entities import MedicineProduct
from backend.domain.medicine.identifiers import YjCode
from backend.domain.medicine.primitives import (
    BrandName,
    GenericName,
)
from backend.domain.medicine.value_objects import MedicineNames
from backend.domain.retrieval.primitives import IntentName, Probability
from backend.domain.retrieval.value_objects import IntentCandidate
from backend.infrastructure.morphology.janome_keyword_extractor import (
    JanomeKeywordExtractor,
)
from backend.infrastructure.package_insert_definitions.loader import (
    get_package_insert_definitions,
)
from backend.infrastructure.persistence.postgres_runtime import _Scope


class FakeJevIntentClassifier:
    is_available = True

    def __init__(self):
        self.completed = False

    async def classify(self, request: IntentRequest) -> IntentResult:
        await asyncio.sleep(0)
        self.completed = True
        return IntentResult(
            True,
            {
                "answers": {
                    "intent": {"choice": "warnings", "probabilities": {"warnings": 0.9}}
                }
            },
            (IntentCandidate(IntentName("warnings"), Probability(0.9)),),
            "warnings",
            True,
        )


class EvidenceSearchTests(unittest.IsolatedAsyncioTestCase):
    async def test_three_detectors_are_collected_before_search(self):
        catalog = get_package_insert_definitions()
        classifier = FakeJevIntentClassifier()
        extractor = JanomeKeywordExtractor(
            search_policy=catalog.text_search_policy,
            morphology_settings=catalog.morphology_settings,
        )
        completed = []

        class Keywords:
            def extract_keywords(self, text: str):
                result = extractor.extract_keywords(text)
                completed.append(True)
                return result

        class Medicines:
            async def read_medicines(self):
                return (
                    RegisteredMedicine(
                        medicine=MedicineProduct(
                            yj_code=YjCode("3339003F5020"),
                            names=MedicineNames(
                                brand_name=BrandName("テスト薬"),
                                generic_name=GenericName("テスト成分"),
                                english_name=None,
                                hiragana_name=None,
                            ),
                        ),
                        reference=MedicineDocumentReference(
                            document_id=DocumentId("test_001"),
                            pmda_url=PmdaUrl("https://example.test"),
                            revision=AttachmentProductRevision({}),
                        ),
                    ),
                )

        class Reader:
            def __init__(self):
                self.conditions = []

            async def search(self, criteria, medicines):
                assert classifier.completed and completed
                self.conditions.append(criteria)
                return ()

        reader = Reader()
        reply = await retrieve_evidence(
            "副作用の頭痛について",
            ["3339003F5020"],
            medicine_reader=Medicines(),
            evidence_reader=reader,
            intent_classifier=classifier,
            keyword_extractor=Keywords(),
            intent_policy=catalog.intent_policy,
        )
        self.assertEqual(
            {condition.source for condition in reader.conditions},
            {"jev", "keyword", "logic"},
        )
        self.assertEqual(reply.retrieval_strategy, "three_detectors")
        assert reply.jev_response is not None
        self.assertEqual(reply.jev_response["qualifying_intents"], ["warnings"])

    async def test_criteria_collection_does_not_search(self):
        catalog = get_package_insert_definitions()
        with patch.object(
            _Scope,
            "search",
            side_effect=AssertionError("検索を実行してはいけない"),
        ) as search:
            conditions, _, _ = await collect_search_criteria(
                FakeJevIntentClassifier(),
                JanomeKeywordExtractor(
                    search_policy=catalog.text_search_policy,
                    morphology_settings=catalog.morphology_settings,
                ),
                "副作用の頭痛について",
                [],
                intent_policy=catalog.intent_policy,
            )
        self.assertTrue(conditions)
        search.assert_not_called()
