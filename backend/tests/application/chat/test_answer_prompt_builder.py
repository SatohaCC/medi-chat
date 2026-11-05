"""Tests for citation metadata included in the grounded LLM prompt."""

from __future__ import annotations

import unittest

from backend.application.chat.queries.policies.answer_prompt import (
    build_answer_system_prompt,
)
from backend.application.indexing.queries.models import DocumentRevision
from backend.application.indexing.values import SearchUnitId, SearchUnitKind
from backend.application.medicine.queries.models import ResolvedMedicine
from backend.application.retrieval.queries.models import Evidence as ChatSource
from backend.application.retrieval.queries.models import (
    EvidenceColumns,
    EvidenceReference,
    EvidenceSection,
)
from backend.application.retrieval.values import (
    EvidenceExcerpt,
    EvidenceGenericName,
    EvidenceProductName,
    EvidenceSourceUrl,
)
from backend.domain.medicine.identifiers import YjCode
from backend.domain.medicine.primitives import BrandName, GenericName
from backend.domain.medicine.value_objects import MedicineMatch as DomainMedicineMatch
from backend.domain.package_insert.identifiers import DocumentId
from backend.infrastructure.package_insert_definitions.definition_assembly import (
    get_package_insert_definitions,
)


class AnswerPromptBuilderTests(unittest.TestCase):
    def test_prompt_formats_xml_grouped_by_medicine_and_omits_references(self) -> None:
        source1 = ChatSource(
            unit_id=SearchUnitId("unit-1"),
            document_id=DocumentId("doc-1"),
            product_name=EvidenceProductName("テスト錠"),
            generic_name=EvidenceGenericName("テスト成分"),
            product_yj_codes=(YjCode("1234567A8901"),),
            document_revision=DocumentRevision(
                {
                    "source_label": "今回",
                    "year_month": "2026-09",
                    "version": "第2版",
                }
            ),
            section=EvidenceSection({"code": "10.1", "title": "併用禁忌"}),
            kind=SearchUnitKind("interaction_row"),
            excerpt=EvidenceExcerpt("本文"),
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
            url=EvidenceSourceUrl("https://example.test/doc#section-10-1"),
        )
        source2 = ChatSource(
            unit_id=SearchUnitId("unit-2"),
            document_id=DocumentId("doc-1"),
            product_name=EvidenceProductName("テスト錠"),
            generic_name=EvidenceGenericName("テスト成分"),
            product_yj_codes=(YjCode("1234567A8901"),),
            document_revision=DocumentRevision(
                {
                    "source_label": "今回",
                    "year_month": "2026-09",
                    "version": "第2版",
                }
            ),
            section=EvidenceSection({"code": "11.1", "title": "重大な副作用"}),
            kind=SearchUnitKind("text"),
            excerpt=EvidenceExcerpt("ショックがあらわれることがある。"),
            url=EvidenceSourceUrl("https://example.test/doc#section-10-1"),
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
            [source1, source2],
            [medicine],
            "interaction",
            answer_prompt_policy=get_package_insert_definitions().answer_prompt_policy,
        )

        self.assertIn("<provided_package_inserts>", prompt)
        self.assertIn('product="テスト錠"', prompt)
        self.assertIn('yj_code="1234567A8901"', prompt)
        self.assertIn('revision="今回 / 2026-09 / 第2版"', prompt)
        self.assertIn('url="https://example.test/doc#section-10-1"', prompt)
        self.assertIn(
            '<evidence id="1" unit_id="unit-1" section="10.1 併用禁忌">', prompt
        )
        self.assertIn(
            '<evidence id="2" unit_id="unit-2" section="11.1 重大な副作用">', prompt
        )
        self.assertIn("薬剤名: 相手薬", prompt)
        self.assertIn("ショックがあらわれることがある。", prompt)
        self.assertNotIn("参照先", prompt)
        self.assertNotIn("HeaderRef", prompt)
        self.assertEqual(prompt.count("<package_insert "), 1)
        self.assertIn("改訂情報と出典URLを明記", prompt)


if __name__ == "__main__":
    unittest.main()
