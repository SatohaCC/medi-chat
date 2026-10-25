"""Validate a PMDA XML document and write derived JSON artifacts."""

from __future__ import annotations

import hashlib
import html
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import PurePosixPath
from typing import Any

from backend.application.attachment_import.errors import InvalidAttachment
from backend.infrastructure.package_insert_definitions.definition_assembly import (
    get_package_insert_definitions,
)
from backend.infrastructure.package_insert_definitions.definition_settings import (
    PmdaXmlSettings,
)
from backend.infrastructure.pmda_xml.search_unit_mapping import make_units
from backend.infrastructure.pmda_xml.section_mapping import make_section_index
from backend.infrastructure.pmda_xml.xml_node_mapping import (
    attr_name,
    build_paths,
    direct_child,
    field,
    metadata,
    source_node,
    tag_name,
    text_of,
)
from backend.infrastructure.serialization.search_payload_codec import (
    DOCUMENT_SCHEMA_VERSION,
    SEARCH_SCHEMA_VERSION,
)


def build_artifacts(
    root: ET.Element,
    *,
    source_filename: str,
    source_sha256: str,
    assets: dict[str, bytes],
    strict_assets: bool,
    xml_settings: PmdaXmlSettings | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    if xml_settings is None:
        xml_settings = get_package_insert_definitions().xml_settings
    if tag_name(root) != "PackIns" or root.attrib.get("drugType") != "Medicine":
        raise InvalidAttachment(
            "unsupported_pmda_document", "Expected a PMDA medicine PackIns document"
        )
    namespace = (
        str(root.tag).split("}", 1)[0].lstrip("{") if "}" in str(root.tag) else None
    )
    parents, paths = build_paths(root)
    insert_no = field(root, "PackageInsertNo", xml_settings=xml_settings)
    company = field(root, "CompanyIdentifier", xml_settings=xml_settings)
    if not insert_no or not company:
        raise InvalidAttachment(
            "missing_document_identity", "Document identity is required"
        )
    pmda_key = f"{company}_{insert_no}"
    pmda_url = f"https://www.pmda.go.jp/PmdaSearch/iyakuDetail/{pmda_key}"
    doc_meta = metadata(root, pmda_url, xml_settings=xml_settings)
    sections, section_by_element = make_section_index(
        root, parents, paths, pmda_url, xml_settings=xml_settings
    )
    root_misc = [
        child
        for child in root
        if tag_name(child) in {"#comment", "#processing_instruction"}
    ]
    unknown_root = [
        tag_name(child)
        for child in root
        if tag_name(child)
        not in xml_settings.header_tags
        | xml_settings.sections_by_xml_tag.keys()
        | {"#comment", "#processing_instruction"}
    ]
    if unknown_root:
        raise InvalidAttachment("unmapped_root_section", "Unknown root section")
    if not sections:
        raise InvalidAttachment("missing_sections", "No known numbered sections found")
    ids = {
        element.attrib["id"]: element
        for element in root.iter()
        if "id" in element.attrib
    }
    all_refs = [
        {"kind": tag_name(element), "target": element.attrib.get("ref")}
        for element in root.iter()
        if tag_name(element) in xml_settings.reference_tags
    ]
    all_refs += [
        {"kind": name, "target": element.attrib[name]}
        for element in root.iter()
        for name in ("categoryRef", "frequencyRef")
        if name in element.attrib
    ]
    unresolved_refs = [ref for ref in all_refs if ref["target"] not in ids]
    asset_records = []
    for filename in dict.fromkeys(
        element.attrib["gfname"]
        for element in root.iter()
        if "gfname" in element.attrib
    ):
        data = assets.get(filename)
        assets_record = {
            "file": str(PurePosixPath(source_filename).parent / filename)
            if strict_assets
            else filename,
            "exists": data is not None,
            "sha256": hashlib.sha256(data).hexdigest() if data is not None else None,
        }
        asset_records.append(assets_record)
    units, covered_langs = make_units(
        root,
        parents,
        paths,
        section_by_element,
        pmda_key,
        pmda_url,
        doc_meta["products"],
        xml_settings=xml_settings,
    )
    section_langs = {
        element
        for child in root
        if tag_name(child) not in xml_settings.header_tags
        for element in child.iter()
        if tag_name(element) == "Lang"
    }
    uncovered = [paths[element] for element in section_langs - covered_langs]
    unit_texts = [html.unescape(unit["text"]) for unit in units]
    duplicate_section_codes = sorted(
        code
        for code, count in Counter(unit["section"]["code"] for unit in units).items()
        if count > 1
    )
    duplicate_unit_ids = sorted(
        unit_id
        for unit_id, count in Counter(unit["unit_id"] for unit in units).items()
        if count > 1
    )
    unrepresented_text = [
        paths[element]
        for element in section_langs
        if text_of(element, xml_settings=xml_settings)
        and not any(
            text_of(element, xml_settings=xml_settings) in unit_text
            for unit_text in unit_texts
        )
    ]

    def section_record(element: ET.Element, sec: dict[str, Any]) -> dict[str, Any]:
        header = direct_child(element, "Header")
        return {
            "code": sec["code"],
            "title": sec["title"],
            "header": text_of(header, xml_settings=xml_settings)
            if header is not None
            else None,
            "xml_id": sec.get("xml_id"),
            "xml_path": sec["xml_path"],
            "tree": source_node(element),
            "children": [
                section_record(child_element, child)
                for child_element, child in section_by_element.items()
                if child["parent_code"] == sec["code"]
            ],
        }

    document = {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "source": {
            "file": source_filename,
            "sha256": source_sha256,
            "namespace": namespace,
            "pmda_url": pmda_url,
            "figures": asset_records,
        },
        "document": doc_meta,
        "root_attributes": {attr_name(k): v for k, v in root.attrib.items()},
        "root_misc_nodes": [
            {"xml_path": paths[element], "tree": source_node(element)}
            for element in root_misc
        ],
        "header_nodes": [
            source_node(child)
            for child in root
            if tag_name(child) in xml_settings.header_tags
        ],
        "section_index": sections,
        "sections": [
            section_record(element, sec)
            for element, sec in section_by_element.items()
            if sec["parent_code"] is None
        ],
    }
    validation = {
        "source_file": source_filename,
        "document_key": pmda_key,
        "xml_element_count": sum(
            isinstance(element.tag, str) for element in root.iter()
        ),
        "processing_instruction_count": sum(
            tag_name(element) == "#processing_instruction" for element in root.iter()
        ),
        "xml_lang_count": sum(tag_name(element) == "Lang" for element in root.iter()),
        "section_lang_count": len(section_langs),
        "covered_section_lang_count": len(section_langs & covered_langs),
        "uncovered_section_lang_paths": sorted(uncovered),
        "unrepresented_nonempty_lang_paths": sorted(unrepresented_text),
        "section_count": len(document["sections"]),
        "numbered_section_count": len(sections),
        "search_schema_version": SEARCH_SCHEMA_VERSION,
        "search_unit_count": len(
            {unit["section"]["code"].split(".", 1)[0] for unit in units}
        ),
        "search_unit_types": {
            "section": len({unit["section"]["code"].split(".", 1)[0] for unit in units})
        },
        "duplicate_section_codes": duplicate_section_codes,
        "duplicate_unit_ids": duplicate_unit_ids,
        "reference_count": len(all_refs),
        "unresolved_references": unresolved_refs,
        "missing_figures": [
            asset["file"] for asset in asset_records if not asset["exists"]
        ],
        "status": "pass"
        if not uncovered
        and not duplicate_section_codes
        and not duplicate_unit_ids
        and not unrepresented_text
        and not unresolved_refs
        and all(asset["exists"] for asset in asset_records)
        else "fail",
        "notes": [
            "項目番号は医療用医薬品の記載要領に対応する明示的なタグ表で付与した。",
            "原文の解釈や禁忌判定は生成していない。検索単位は原文階層からの派生データ。",
            "XSDによる妥当性検証とPMDA表示との差分照合は未実施。",
        ],
    }
    if duplicate_section_codes or duplicate_unit_ids:
        raise InvalidAttachment("duplicate_section", "Duplicate numbered section")
    if unresolved_refs:
        raise InvalidAttachment(
            "unresolved_reference", "Internal reference is unresolved"
        )
    if uncovered or unrepresented_text:
        raise InvalidAttachment(
            "unrepresented_body", "Original body is not represented"
        )
    if validation["missing_figures"]:
        if strict_assets:
            raise InvalidAttachment("missing_figure", "Required figure is missing")
        validation["status"] = "warning"
    return document, units, validation
