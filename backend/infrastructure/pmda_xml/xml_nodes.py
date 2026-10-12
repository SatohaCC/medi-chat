"""XML tree preservation, text rendering, and document metadata."""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any

from package_inserts.catalog_loader import get_package_insert_catalog

PROJECT_ROOT = Path(__file__).resolve().parents[3]

SUPERSCRIPTS = str.maketrans("0123456789+-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻")


def tag_name(element: ET.Element) -> str:
    if element.tag is ET.ProcessingInstruction:
        return "#processing_instruction"
    if element.tag is ET.Comment:
        return "#comment"
    return str(element.tag).rsplit("}", 1)[-1]


def attr_name(name: str) -> str:
    if name.startswith("{http://www.w3.org/XML/1998/namespace}"):
        return "xml:" + name.rsplit("}", 1)[-1]
    return name.rsplit("}", 1)[-1]


def relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.name


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_node(element: ET.Element) -> dict[str, Any]:
    """Keep every XML node, attribute, text, tail, and processing instruction."""
    node: dict[str, Any] = {"tag": tag_name(element)}
    if element.attrib:
        node["attributes"] = {attr_name(k): v for k, v in element.attrib.items()}
    if element.text is not None:
        node["text"] = element.text
    if element.tail is not None:
        node["tail"] = element.tail
    if len(element):
        node["children"] = [source_node(child) for child in element]
    return node


def build_paths(
    root: ET.Element,
) -> tuple[dict[ET.Element, ET.Element], dict[ET.Element, str]]:
    parents: dict[ET.Element, ET.Element] = {}
    paths = {root: f"/{tag_name(root)}[1]"}

    def walk(element: ET.Element) -> None:
        counts: Counter[str] = Counter()
        for child in element:
            name = tag_name(child)
            counts[name] += 1
            parents[child] = element
            paths[child] = f"{paths[element]}/{name}[{counts[name]}]"
            walk(child)

    walk(root)
    return parents, paths


def direct_child(element: ET.Element, name: str) -> ET.Element | None:
    return next((child for child in element if tag_name(child) == name), None)


def find_path(element: ET.Element, *names: str) -> ET.Element | None:
    current: ET.Element | None = element
    for name in names:
        if current is None:
            return None
        current = direct_child(current, name)
    return current


def render_inline(element: ET.Element) -> str:
    tag = tag_name(element)
    if tag == "#processing_instruction":
        return "\ue000" if (element.text or "").split(" ", 1)[0] == "enter" else ""
    if tag in get_package_insert_catalog().xml.reference_tags:
        return ""
    if tag in {"InlineGraphic", "GraphicBody"}:
        return f"［図:{element.attrib.get('gfname', '')}］"
    if tag == "Sup":
        return render_children(element).translate(SUPERSCRIPTS)
    if tag == "Sub":
        return "_{" + render_children(element) + "}"
    return render_children(element)


def render_children(element: ET.Element) -> str:
    pieces = [element.text or ""]
    for child in element:
        pieces.append(render_inline(child))
        tail = child.tail or ""
        if tag_name(
            child
        ) in get_package_insert_catalog().xml.reference_tags and re.fullmatch(
            r"[\s,，、]*", tail
        ):
            tail = ""
        pieces.append(tail)
    return "".join(pieces)


def clean_text(raw: str) -> str:
    chunks = [re.sub(r"\s+", " ", part).strip() for part in raw.split("\ue000")]
    return "\n".join(chunk for chunk in chunks if chunk)


def text_of(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return clean_text(render_inline(element))


def text_lines(element: ET.Element | None) -> list[str]:
    if element is None:
        return []
    lines = []
    for child in element.iter():
        if tag_name(child) == "Lang":
            value = text_of(child)
            if value:
                lines.append(value)
    return lines


def field(element: ET.Element, *names: str) -> str | None:
    value = text_of(find_path(element, *names))
    return value or None


def metadata(root: ET.Element, pmda_url: str) -> dict[str, Any]:
    approval = direct_child(root, "ApprovalEtc")
    products: list[dict[str, Any]] = []
    if approval is not None:
        for brand in approval:
            if tag_name(brand) != "DetailBrandName":
                continue
            products.append(
                {
                    "xml_id": brand.attrib.get("id"),
                    "brand_name": field(brand, "ApprovalBrandName"),
                    "yj_code": field(brand, "BrandCode", "YJCode"),
                    "english_name": field(brand, "TrademarkInEnglish", "TrademarkName"),
                    "hiragana_name": field(
                        brand, "BrandNameInHiragana", "NameInHiragana"
                    ),
                    "approval_no": field(brand, "ApprovalAndLicenseNo", "ApprovalNo"),
                    "marketing_start_month": field(brand, "StartingDateOfMarketing"),
                    "storage_method": field(brand, "Storage", "StorageMethod"),
                    "shelf_life": field(brand, "Storage", "ShelfLife"),
                }
            )
    revisions = []
    revision_parent = direct_child(root, "DateOfPreparationOrRevision")
    if revision_parent is not None:
        for entry in revision_parent:
            if tag_name(entry) == "PreparationOrRevision":
                revisions.append(
                    {
                        "source_label": entry.attrib.get("id"),
                        "year_month": field(entry, "YearMonth"),
                        "version": field(entry, "Version"),
                    }
                )
    return {
        "package_insert_no": field(root, "PackageInsertNo"),
        "company_identifier": field(root, "CompanyIdentifier"),
        "drug_type": root.attrib.get("drugType"),
        "xml_kind": root.attrib.get("xmlKind"),
        "xml_version": root.attrib.get("version"),
        "revisions": revisions,
        "japanese_standard_commodity_classification": field(root, "Sccj", "SccjNo"),
        "therapeutic_classification": field(root, "TherapeuticClassification"),
        "generic_name": field(root, "GenericName"),
        "products": products,
        "pmda_url": pmda_url,
    }
