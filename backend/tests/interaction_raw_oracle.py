"""Independent R6 source reader. No application decoder/catalog imports."""

import hashlib
import re
from pathlib import Path
from typing import TypedDict
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
DOCUMENTS = (
    (
        "630004_3339003F5020_1_08",
        "2e04312381822dca6fd8a3d0c4c2dfac74a9d0bbec9a0f9e6bd02b6b8c11856c",
        "3339003F5020",
    ),
    (
        "800155_6290004M1029_1_47",
        "53eb95df5383e8883dc97a3d0537fba3d5bc530acf1a8726ecce44b8f548e08b",
        "6290004M1029",
    ),
    (
        "300119_6290004M1070_1_17",
        "14a47118a9d65104e16837e32d88b9c4eb6ce9ad730068f8a7fdcc5342ce8efc",
        "6290004M1070",
    ),
)
SECTION_TAGS = {
    "10": "Interactions",
    "10.1": "ContraIndicatedCombinations",
    "10.2": "PrecautionsForCombinations",
    "16.7": "DrugAndDrugInteractions",
}
COLUMNS = ("DrugName", "ClinSymptomsAndMeasures", "MechanismAndRiskFactors")


class RawReference(TypedDict):
    kind: str
    target_xml_id: str
    target_section_code: str | None
    target_url: str


class OracleItem(TypedDict):
    xml_id: str
    header: str
    text: str
    references: list[RawReference]


def name(node):
    return str(node.tag).rsplit("}", 1)[-1]


def visible(node):
    if node.tag is ET.ProcessingInstruction:
        return "\n" if (node.text or "").split()[0] == "enter" else ""
    if name(node).endswith("Ref"):
        return ""
    parts = [node.text or ""]
    for child in node:
        parts.append(visible(child))
        tail = child.tail or ""
        if name(child).endswith("Ref") and not tail.strip(" ,，、\n\t\r"):
            tail = ""
        parts.append(tail)
    value = "".join(parts)
    if name(node) == "Sub":
        return "_{" + value + "}"
    if name(node) == "Sup":
        return value.translate(str.maketrans("0123456789+-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻"))
    return value


def language_text(node):
    return "\n".join(
        "\n".join(
            re.sub(r"[\t\r ]+", " ", part).strip()
            for part in visible(lang).split("\n")
            if part.strip()
        )
        for lang in node.iter()
        if name(lang) == "Lang" and visible(lang).strip()
    )


def paragraph_text(node):
    return "\n".join(
        re.sub(r"[\t\r ]+", " ", part).strip()
        for part in visible(node).split("\n")
        if part.strip()
    )


def read_raw_oracle():
    documents = []
    for doc, sha, yj in DOCUMENTS:
        path = next((ROOT / "data/pmda/originals").glob(f"*/{doc}.xml"))
        assert hashlib.sha256(path.read_bytes()).hexdigest() == sha
        root = ET.parse(
            path, parser=ET.XMLParser(target=ET.TreeBuilder(insert_pis=True))
        ).getroot()
        parents = {child: parent for parent in root.iter() for child in parent}
        targets = {
            node.attrib["id"]: node for node in root.iter() if "id" in node.attrib
        }
        sections = {}
        for code, tag in SECTION_TAGS.items():
            node = next((item for item in root.iter() if name(item) == tag), None)
            if node is None:
                continue
            own = (
                next(
                    (child for child in node if name(child) == "SummaryOfCombination"),
                    node,
                )
                if code == "10"
                else node
            )
            rows = []
            if code in {"10.1", "10.2"}:
                for drug in node.iter():
                    if name(drug) == "Drug":
                        rows.append(
                            [
                                language_text(cell)
                                if (
                                    cell := next(
                                        (
                                            child
                                            for child in drug
                                            if name(child) == column
                                        ),
                                        None,
                                    )
                                )
                                is not None
                                else ""
                                for column in COLUMNS
                            ]
                        )
            body = []
            if not rows:
                for lang in own.iter():
                    if name(lang) != "Lang":
                        continue
                    if visible(lang).strip():
                        text = "\n".join(
                            re.sub(r"[\t\r ]+", " ", part).strip()
                            for part in visible(lang).split("\n")
                            if part.strip()
                        )
                        if text not in body:
                            body.append(text)
            items: list[OracleItem] = []
            if code == "16.7":
                body = []
                ordered = next(child for child in own if name(child) == "OrderedList")
                for item in ordered:
                    parts = [
                        child for child in item if name(child) in {"Header", "Detail"}
                    ]
                    text = "\n".join(
                        paragraph_text(part) for part in parts if paragraph_text(part)
                    )
                    header = next(child for child in item if name(child) == "Header")
                    items.append(
                        {
                            "xml_id": item.attrib["id"],
                            "header": paragraph_text(header),
                            "text": text,
                            "references": [],
                        }
                    )
                    body.append(text)
                for child in own:
                    if name(child) == "Detail":
                        body.append(paragraph_text(child))
            refs = []
            occurrences = []
            for ref in own.iter():
                if not name(ref).endswith("Ref"):
                    continue
                target_id = ref.attrib["ref"]
                target = targets[target_id]
                chain = target
                target_code = None
                while chain is not None:
                    t = name(chain)
                    if t == "ContraIndications":
                        target_code = "2"
                    elif t == "DrugAndDrugInteractions":
                        target_code = "16.7"
                    elif t == "Metabolism":
                        target_code = "16.4"
                    elif t in {
                        "References",
                        "ReferencesToLiterature",
                        "MainLiterature",
                    }:
                        target_code = "23"
                    elif t in {
                        "ImportantPrecautions",
                        "InfoPrecautionsDosage",
                        "PatientsWithHepaticImpairment",
                        "PatientsWithRenalImpairment",
                    }:
                        target_code = {
                            "ImportantPrecautions": "8",
                            "InfoPrecautionsDosage": "7",
                            "PatientsWithHepaticImpairment": "9.3",
                            "PatientsWithRenalImpairment": "9.2",
                        }[t]
                    elif t in SECTION_TAGS.values():
                        target_code = next(k for k, v in SECTION_TAGS.items() if v == t)
                    if target_code:
                        break
                    chain = parents.get(chain)
                if (
                    target is not chain
                    and name(target) == "Item"
                    and target_code in {"2", "16.7", "8", "7", "9.2", "9.3"}
                ):
                    assert chain is not None
                    target_items = [
                        item
                        for item in chain.iter()
                        if name(item) == "Item" and item.attrib.get("id")
                    ]
                    target_code += "." + str(target_items.index(target) + 1)
                entry: RawReference = {
                    "kind": name(ref),
                    "target_xml_id": target_id,
                    "target_section_code": target_code,
                    "target_url": f"https://www.pmda.go.jp/PmdaSearch/iyakuDetail/{doc}#{target_id}",
                }
                refs.append(entry)
                if code == "16.7":
                    owner = parents[ref]
                    while name(owner) != "Item":
                        owner = parents[owner]
                    lang = parents[ref]
                    while name(lang) != "Lang":
                        lang = parents[lang]
                    languages = [
                        child for child in owner.iter() if name(child) == "Lang"
                    ]
                    inline_refs = [
                        child for child in lang.iter() if name(child).endswith("Ref")
                    ]
                    occurrences.append(
                        {
                            "owner_xml_id": owner.attrib["id"],
                            "language_index": languages.index(lang),
                            "reference_index": inline_refs.index(ref),
                            "reference": entry,
                        }
                    )
                    group = next(
                        item for item in items if item["xml_id"] == owner.attrib["id"]
                    )
                    if entry not in group["references"]:
                        group["references"].append(entry)
            if code == "16.7":
                refs = [reference for item in items for reference in item["references"]]
            sections[code] = {
                "unit_id": f"{doc}:{sha}:{code}",
                "rows": rows,
                "body": body,
                "references": refs,
            }
            if code == "16.7":
                sections[code]["items"] = items
                sections[code]["raw_reference_occurrences"] = occurrences
        product = next(
            node for node in root.iter() if name(node) == "ApprovalBrandName"
        )
        generic = next(node for node in root if name(node) == "GenericName")
        revision = next(
            node
            for node in root.iter()
            if name(node) == "PreparationOrRevision" and node.attrib.get("id") == "今回"
        )
        documents.append(
            {
                "document_id": doc,
                "sha256": sha,
                "yj": yj,
                "product_name": language_text(product),
                "generic_name": language_text(generic),
                "revision": {
                    "source_label": "今回",
                    "year_month": visible(
                        next(child for child in revision if name(child) == "YearMonth")
                    ).strip(),
                    "version": language_text(
                        next(child for child in revision if name(child) == "Version")
                    ),
                },
                "sections": sections,
            }
        )
    return documents
