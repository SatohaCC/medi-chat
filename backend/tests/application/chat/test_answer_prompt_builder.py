"""Tests for citation metadata included in the grounded LLM prompt."""

from __future__ import annotations

import unittest

from backend.application.chat.answer_prompt_builder import build_answer_system_prompt
from backend.application.medicine.product_models import ResolvedMedicine
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.medicine.identifiers import YjCode
from backend.domain.medicine.primitives import BrandName, GenericName
from backend.domain.medicine.value_objects import MedicineMatch as DomainMedicineMatch
from backend.domain.retrieval.identifiers import SearchUnitId
from backend.domain.retrieval.value_objects import (
    DocumentRevision,
    EvidenceColumns,
    EvidenceReference,
    EvidenceSection,
)
from backend.domain.retrieval.value_objects import Evidence as ChatSource
from backend.infrastructure.package_insert_definitions.loader import (
    get_package_insert_definitions,
)


class AnswerPromptBuilderTests(unittest.TestCase):
    def test_prompt_contains_revision_url_and_references(self) -> None:
        source = ChatSource(
            unit_id=SearchUnitId("unit-1"),
            document_id=DocumentId("doc-1"),
            product_name="テスト錠",
            generic_name="テスト成分",
            product_yj_codes=(YjCode("1234567A8901"),),
            document_revision=DocumentRevision(
                {
                    "source_label": "今回",
                    "year_month": "2026-09",
                    "version": "第2版",
                }
            ),
            section=EvidenceSection({"code": "10.1", "title": "併用禁忌"}),
            kind="interaction_row",
            excerpt="本文",
            columns=EvidenceColumns(
                {
                    "drug_name": "相手薬",
                    "clinical_symptoms_and_measures": "臨床症状",
                    "mechanism_and_risk_factors": "機序",
                }
            ),
            references=(
                EvidenceReference(
                    {
                        "kind": "HeaderRef",
                        "target_section_code": "2",
                        "target_url": "https://example.test/doc#section-2",
                    }
                ),
            ),
            url="https://example.test/doc#section-10-1",
        )
        medicine = ResolvedMedicine(
            medicine=DomainMedicineMatch(
                generic_name=GenericName("テスト成分"),
                brand_names=tuple(BrandName(value) for value in ("テスト錠",)),
                yj_codes=tuple(YjCode(value) for value in ("1234567A8901",)),
            ),
            document_ids=("doc-1",),
        )

        prompt = build_answer_system_prompt(
            [source],
            [medicine],
            "interaction",
            answer_prompt_policy=get_package_insert_definitions().answer_prompt_policy,
        )

        self.assertIn("1234567A8901", prompt)
        self.assertIn("今回 / 2026-09 / 第2版", prompt)
        self.assertIn("https://example.test/doc#section-10-1", prompt)
        self.assertIn("項目 2", prompt)
        self.assertIn("https://example.test/doc#section-2", prompt)
        self.assertIn("改訂情報と出典URLを明記", prompt)


if __name__ == "__main__":
    unittest.main()
