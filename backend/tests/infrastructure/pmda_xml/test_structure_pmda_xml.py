"""Regression checks for relationships that must survive XML conversion."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

import pytest
from backend.infrastructure.package_insert_definitions.loader import (
    get_package_insert_definitions,
)
from backend.infrastructure.pmda_xml.transform import transform
from backend.tests.support.paths import PROJECT_ROOT
from backend.tests.support.section_records import flatten_sections

pytestmark = pytest.mark.source_data


DATA_DIR = PROJECT_ROOT / "data/pmda/originals"
SOURCE = DATA_DIR / "イグザレルト錠２．５ｍｇ" / "630004_3339003F5020_1_08.xml"
ADDED_SOURCES = [
    DATA_DIR / "イトリゾールカプセル５０" / "800155_6290004M1029_1_47.xml",
    DATA_DIR
    / "イトラコナゾールカプセル５０ｍｇ「ＳＷ」"
    / "300119_6290004M1070_1_17.xml",
]


class StructurePmdaXmlTests(unittest.TestCase):
    temp_dir: tempfile.TemporaryDirectory[str]
    validation: dict[str, Any]
    document: dict[str, Any]
    units: list[dict[str, Any]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        output = Path(cls.temp_dir.name)
        cls.validation = transform(SOURCE, output)
        cls.document = json.loads(
            (output / "document.json").read_text(encoding="utf-8")
        )
        cls.units = [
            json.loads(line)
            for line in (output / "search_units.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_dir.cleanup()

    def test_source_coverage_and_links(self) -> None:
        self.assertEqual(self.validation["status"], "pass")
        self.assertEqual(
            self.validation["section_lang_count"],
            self.validation["covered_section_lang_count"],
        )
        self.assertEqual(self.validation["unrepresented_nonempty_lang_paths"], [])
        self.assertEqual(self.validation["unresolved_references"], [])
        self.assertEqual(self.validation["missing_figures"], [])
        self.assertEqual(self.validation["processing_instruction_count"], 118)
        self.assertEqual(len({unit["unit_id"] for unit in self.units}), len(self.units))

    def test_indication_scopes_stay_separate(self) -> None:
        contraindications = next(
            unit for unit in self.units if unit["section"]["code"] == "2"
        )
        paragraphs = [
            block
            for block in contraindications["blocks"]
            if block["kind"] == "paragraph"
        ]
        pad = next(block for block in paragraphs if "eGFR15" in block["text"])
        fontan = next(block for block in paragraphs if "eGFR30" in block["text"])
        self.assertNotEqual(pad["context"]["labels"], fontan["context"]["labels"])
        self.assertIn("下肢血行再建術", pad["context"]["labels"][-1])
        self.assertIn("Fontan", fontan["context"]["labels"][-1])

    def test_indications_keep_original_labels_as_body_without_invented_headings(
        self,
    ) -> None:
        sec4_units = [u for u in self.units if u["section"]["code"] == "4"]
        self.assertEqual(len(sec4_units), 1)
        sec4_texts = [u["text"] for u in sec4_units]
        self.assertNotIn("成人", sec4_texts)
        self.assertNotIn("小児", sec4_texts)
        self.assertTrue(
            any(
                "成人" in t
                and "下肢血行再建術施行後の末梢動脈疾患患者における血栓・塞栓形成の抑制"
                in t
                for t in sec4_texts
            )
        )
        self.assertTrue(
            any(
                "小児" in t and "Fontan手術施行後における血栓・塞栓形成の抑制" in t
                for t in sec4_texts
            )
        )

    def test_interactions_and_adverse_events_keep_table_meaning(self) -> None:
        sections = {unit["section"]["code"]: unit for unit in self.units}
        self.assertEqual(sections["10"]["text"].count("<tr>"), 15)
        for column in get_package_insert_definitions().interaction_columns:
            self.assertIn(column.title.value, sections["10"]["text"])
        self.assertEqual(sections["11"]["text"].count("<tr>"), 34)
        self.assertIn("頻度", sections["11"]["text"])
        self.assertIn("分類", sections["11"]["text"])
        self.assertTrue(
            any(
                'rowspan="' in unit["text"] or 'colspan="' in unit["text"]
                for unit in self.units
            )
        )
        self.assertEqual(len(self.document["source"]["figures"]), 6)

    def test_added_xml_documents_include_new_sections_and_all_text(self) -> None:
        for source in ADDED_SOURCES:
            with (
                self.subTest(source=source.name),
                tempfile.TemporaryDirectory() as temp_dir,
            ):
                output = Path(temp_dir)
                validation = transform(source, output)
                document = json.loads(
                    (output / "document.json").read_text(encoding="utf-8")
                )
                units = [
                    json.loads(line)
                    for line in (output / "search_units.jsonl")
                    .read_text(encoding="utf-8")
                    .splitlines()
                ]
                section_codes = {
                    section["code"] for section in document["section_index"]
                }
                self.assertEqual(validation["status"], "pass")
                self.assertEqual(validation["unrepresented_nonempty_lang_paths"], [])
                self.assertTrue({"5", "20"}.issubset(section_codes))
                self.assertTrue(document["root_misc_nodes"])
                graphics = [
                    block
                    for unit in units
                    for block in unit["blocks"]
                    if block["kind"] == "figure"
                ]
                self.assertTrue(graphics)
                self.assertTrue(all(block["reference"] for block in graphics))
                if source.name == "800155_6290004M1029_1_47.xml":
                    self.assertTrue(any(block["description"] for block in graphics))

    def test_reproductive_potential_is_section_9_4_in_both_xml_documents(self) -> None:
        for source in ADDED_SOURCES:
            with (
                self.subTest(source=source.name),
                tempfile.TemporaryDirectory() as temp_dir,
            ):
                output = Path(temp_dir)
                validation = transform(source, output)
                document = json.loads(
                    (output / "document.json").read_text(encoding="utf-8")
                )
                units = [
                    json.loads(line)
                    for line in (output / "search_units.jsonl")
                    .read_text(encoding="utf-8")
                    .splitlines()
                ]

                reproductive_section = next(
                    section
                    for section in document["section_index"]
                    if section["code"] == "9.4"
                )
                self.assertEqual(reproductive_section["title"], "生殖能を有する者")
                self.assertEqual(
                    reproductive_section["xml_tag"],
                    "MalesAndFemalesOfReproductivePotential",
                )
                self.assertEqual(reproductive_section["parent_code"], "9")
                self.assertTrue(
                    {"9.5", "9.6"}.issubset(
                        {section["code"] for section in document["section_index"]}
                    )
                )

                reproductive_unit = next(
                    unit
                    for unit in units
                    if unit["section"]["code"] == "9"
                    and "最終投与後1ヵ月間" in unit["text"]
                )
                self.assertEqual(reproductive_unit["kind"], "section")
                self.assertIn("避妊する必要性", reproductive_unit["text"])
                self.assertTrue(
                    any(
                        reference["target_section_code"] == "9.5"
                        for reference in reproductive_unit["references"]
                    )
                )
                self.assertEqual(validation["status"], "pass")
                self.assertEqual(validation["unrepresented_nonempty_lang_paths"], [])

    def test_optional_standard_sections_are_pre_registered_by_xml_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            source = base / "standard-sections.xml"
            source.write_text(
                """<PackIns drugType="Medicine">
  <PackageInsertNo>test_01</PackageInsertNo>
  <CompanyIdentifier>000001</CompanyIdentifier>
  <InfluenceOnLaboratoryValues><Lang>検査値への影響</Lang></InfluenceOnLaboratoryValues>
  <OverDosage>
    <OrderedList>
      <Item><Header><Lang>症状</Lang></Header><Detail><Lang>過量投与時の症状</Lang></Detail></Item>
      <Item><Header><Lang>13.2 処置</Lang></Header><Detail><Lang>必要な処置</Lang></Detail></Item>
    </OrderedList>
  </OverDosage>
  <OtherPrecautions>
    <InformationBasedOnNonClinicalUse><Lang>非臨床情報</Lang></InformationBasedOnNonClinicalUse>
  </OtherPrecautions>
  <Pharmacokinetics><OtherInformation><Lang>薬物動態のその他</Lang></OtherInformation></Pharmacokinetics>
  <ResultsOfClinicalTrials>
    <PostMarketingSurveillance><Lang>製造販売後調査等</Lang></PostMarketingSurveillance>
    <OtherInformation><Lang>臨床成績のその他</Lang></OtherInformation>
  </ResultsOfClinicalTrials>
  <EfficacyPharmacology>
    <MechanismOfAction><Lang>作用機序</Lang></MechanismOfAction>
    <OtherInformation><Lang>薬理作用</Lang></OtherInformation>
  </EfficacyPharmacology>
  <PrecautionsForApplication><OtherInformation><Lang>適用上のその他</Lang></OtherInformation></PrecautionsForApplication>
  <AttentionOfInsurance><Lang>保険給付上の注意</Lang></AttentionOfInsurance>
  <NameAddressManufact><Manufacturer><Lang>製造販売元</Lang></Manufacturer></NameAddressManufact>
</PackIns>
""",
                encoding="utf-8",
            )
            output = base / "structured"
            validation = transform(source, output)
            document = json.loads(
                (output / "document.json").read_text(encoding="utf-8")
            )
            units = [
                json.loads(line)
                for line in (output / "search_units.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]

        by_code = {section["code"]: section for section in document["section_index"]}
        self.assertEqual(by_code["12"]["xml_tag"], "InfluenceOnLaboratoryValues")
        self.assertEqual(by_code["13"]["title"], "過量投与")
        self.assertEqual(by_code["15.2"]["parent_code"], "15")
        self.assertEqual(by_code["16.8"]["parent_code"], "16")
        self.assertEqual(by_code["17.2"]["parent_code"], "17")
        self.assertEqual(by_code["17.3"]["parent_code"], "17")
        self.assertEqual(by_code["18"]["title"], "薬効薬理")
        self.assertEqual(by_code["25"]["xml_tag"], "AttentionOfInsurance")
        self.assertNotIn("13.1", by_code)
        self.assertNotIn("13.2", by_code)
        self.assertNotIn("18.2", by_code)
        self.assertNotIn("26.1", by_code)
        sections_by_code = {
            s["code"]: s for s in flatten_sections(document["sections"])
        }
        self.assertIn("16.8", sections_by_code)
        self.assertIn("17.3", sections_by_code)
        self.assertEqual(
            next(
                unit["section"]["code"]
                for unit in units
                if "薬物動態のその他" in unit["text"]
            ),
            "16",
        )
        self.assertEqual(
            next(
                unit["section"]["code"]
                for unit in units
                if "臨床成績のその他" in unit["text"]
            ),
            "17",
        )
        self.assertEqual(
            next(
                unit["section"]["code"] for unit in units if "薬理作用" in unit["text"]
            ),
            "18",
        )
        self.assertEqual(
            next(
                unit["section"]["code"]
                for unit in units
                if "適用上のその他" in unit["text"]
            ),
            "14",
        )
        self.assertEqual(
            next(
                unit["section"]["code"]
                for unit in units
                if "製造販売元" in unit["text"]
            ),
            "26",
        )
        self.assertEqual(
            next(
                unit["section"]["code"]
                for unit in units
                if "過量投与時の症状" in unit["text"]
            ),
            "13",
        )
        self.assertEqual(
            next(
                unit["section"]["code"]
                for unit in units
                if "必要な処置" in unit["text"]
            ),
            "13",
        )
        self.assertEqual(validation["status"], "pass")

    def test_all_fixed_numbered_sections_have_a_preconfigured_mapping(self) -> None:
        configured_codes = {
            section.code.value
            for section in get_package_insert_definitions().taxonomy.sections
        }
        expected_codes = {
            "1",
            "2",
            "3",
            "3.1",
            "3.2",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
            "9.1",
            "9.2",
            "9.3",
            "9.4",
            "9.5",
            "9.6",
            "9.7",
            "9.8",
            "10",
            "10.1",
            "10.2",
            "11",
            "11.1",
            "11.2",
            "12",
            "13",
            "14",
            "15",
            "15.1",
            "15.2",
            "16",
            "16.1",
            "16.2",
            "16.3",
            "16.4",
            "16.5",
            "16.6",
            "16.7",
            "16.8",
            "17",
            "17.1",
            "17.2",
            "17.3",
            "18",
            "18.1",
            "19",
            "20",
            "21",
            "22",
            "23",
            "24",
            "25",
            "26",
        }
        self.assertEqual(configured_codes, expected_codes)

    def test_documented_section_tag_aliases_keep_their_fixed_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            source = base / "section-aliases.xml"
            source.write_text(
                """<PackIns drugType="Medicine">
  <PackageInsertNo>test_02</PackageInsertNo>
  <CompanyIdentifier>000001</CompanyIdentifier>
  <EffectsOnLaboratoryTests><Lang>検査値</Lang></EffectsOnLaboratoryTests>
  <OverDosage><Lang>過量投与</Lang></OverDosage>
  <PrecautionsForInsuranceCoverage><Lang>保険</Lang></PrecautionsForInsuranceCoverage>
</PackIns>
""",
                encoding="utf-8",
            )
            output = base / "structured"
            transform(source, output)
            document = json.loads(
                (output / "document.json").read_text(encoding="utf-8")
            )
            by_code = {
                section["code"]: section for section in document["section_index"]
            }
            self.assertEqual(by_code["12"]["xml_tag"], "EffectsOnLaboratoryTests")
            self.assertEqual(by_code["13"]["code"], "13")
            self.assertEqual(
                by_code["25"]["xml_tag"], "PrecautionsForInsuranceCoverage"
            )

            gap_source = base / "section-gap.xml"
            gap_source.write_text(
                """<PackIns drugType="Medicine">
  <PackageInsertNo>test_03</PackageInsertNo>
  <CompanyIdentifier>000001</CompanyIdentifier>
  <OverDosage><Lang>過量投与</Lang></OverDosage>
  <PrecautionsForApplication><Lang>適用上の注意</Lang></PrecautionsForApplication>
</PackIns>
""",
                encoding="utf-8",
            )
            gap_output = base / "gap-structured"
            transform(gap_source, gap_output)
            gap_document = json.loads(
                (gap_output / "document.json").read_text(encoding="utf-8")
            )
            gap_codes = {section["code"] for section in gap_document["section_index"]}
            self.assertNotIn("12", gap_codes)
            self.assertTrue({"13", "14"}.issubset(gap_codes))

    def test_multiproduct_xml_preserves_per_product_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            source = base / "multi-product.xml"
            source.write_text(
                """<PackIns drugType="Medicine">
  <PackageInsertNo>multi_01</PackageInsertNo>
  <CompanyIdentifier>000001</CompanyIdentifier>
  <ApprovalEtc>
    <DetailBrandName id="B1">
      <ApprovalBrandName><Lang>製品A錠10mg</Lang></ApprovalBrandName>
      <BrandCode><YJCode>111111111111</YJCode></BrandCode>
    </DetailBrandName>
    <DetailBrandName id="B2">
      <ApprovalBrandName><Lang>製品B細粒20%</Lang></ApprovalBrandName>
      <BrandCode><YJCode>222222222222</YJCode></BrandCode>
    </DetailBrandName>
  </ApprovalEtc>
  <Warnings><Lang>共通の警告事項</Lang></Warnings>
  <ContraIndications>
    <Item brandRef="B1"><Detail><Lang>製品Aのみの禁忌</Lang></Detail></Item>
    <Item brandRef="B2"><Detail><Lang>製品Bのみの禁忌</Lang></Detail></Item>
  </ContraIndications>
</PackIns>
""",
                encoding="utf-8",
            )
            output = base / "structured"
            validation = transform(source, output)
            self.assertEqual(validation["status"], "pass")
            units = [
                json.loads(line)
                for line in (output / "search_units.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]

        warning_unit = next(u for u in units if "共通の警告事項" in u["text"])
        unit_a = next(u for u in units if "製品Aのみの禁忌" in u["text"])
        unit_b = next(u for u in units if "製品Bのみの禁忌" in u["text"])

        # Warning without brandRef applies to both products
        self.assertEqual(
            set(warning_unit["product_yj_codes"]), {"111111111111", "222222222222"}
        )

        # One section contains both products, with applicability visible in its body.
        self.assertIs(unit_a, unit_b)
        self.assertEqual(
            set(unit_a["product_yj_codes"]), {"111111111111", "222222222222"}
        )
        text = unit_a["text"]
        heading_a = "対象製品: 製品A錠10mg [YJ: 111111111111]"
        heading_b = "対象製品: 製品B細粒20% [YJ: 222222222222]"
        self.assertIn(heading_a, text)
        self.assertIn(heading_b, text)
        first, second = text.split(heading_b)
        self.assertIn("製品Aのみの禁忌", first)
        self.assertNotIn("製品Bのみの禁忌", first)
        self.assertIn("製品Bのみの禁忌", second)
        self.assertNotIn("製品Aのみの禁忌", second)


if __name__ == "__main__":
    unittest.main()
