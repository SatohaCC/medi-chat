"""Validate a PMDA XML document and write derived JSON artifacts."""

from __future__ import annotations

import html
import json
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any

from package_inserts.catalog_loader import get_package_insert_catalog

from .sections import make_section_index
from .units import make_units
from .xml_nodes import (
    attr_name,
    build_paths,
    field,
    metadata,
    relative_path,
    sha256,
    source_node,
    tag_name,
    text_of,
)


def transform(xml_path: Path, output_dir: Path) -> dict[str, Any]:
    catalog = get_package_insert_catalog()
    xml_path = xml_path.resolve()
    if not xml_path.is_file():
        raise FileNotFoundError(xml_path)
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True, insert_pis=True))
    root = ET.parse(xml_path, parser=parser).getroot()
    if tag_name(root) != "PackIns" or root.attrib.get("drugType") != "Medicine":
        raise ValueError("Expected a PMDA prescription-drug PackIns XML")
    namespace = (
        str(root.tag).split("}", 1)[0].lstrip("{") if "}" in str(root.tag) else None
    )
    parents, paths = build_paths(root)
    insert_no = field(root, "PackageInsertNo")
    company = field(root, "CompanyIdentifier")
    if not insert_no or not company:
        raise ValueError("PackageInsertNo and CompanyIdentifier are required")
    pmda_key = f"{company}_{insert_no}"
    pmda_url = f"https://www.pmda.go.jp/PmdaSearch/iyakuDetail/{pmda_key}"
    doc_meta = metadata(root, pmda_url)
    source_sha256 = sha256(xml_path)
    sections, section_by_element = make_section_index(root, parents, paths, pmda_url)
    if not sections:
        raise ValueError("No known numbered sections found")
    root_misc = [
        child
        for child in root
        if tag_name(child) in {"#comment", "#processing_instruction"}
    ]
    unknown_root = [
        tag_name(child)
        for child in root
        if tag_name(child)
        not in catalog.xml.header_tags
        | catalog.sections_by_xml_tag.keys()
        | {"#comment", "#processing_instruction"}
    ]
    if unknown_root:
        raise ValueError(f"Unmapped root sections: {unknown_root}")
    ids = {
        element.attrib["id"]: element
        for element in root.iter()
        if "id" in element.attrib
    }
    all_refs = [
        {"kind": tag_name(element), "target": element.attrib.get("ref")}
        for element in root.iter()
        if tag_name(element) in catalog.xml.reference_tags
    ]
    all_refs += [
        {"kind": name, "target": element.attrib[name]}
        for element in root.iter()
        for name in ("categoryRef", "frequencyRef")
        if name in element.attrib
    ]
    unresolved_refs = [ref for ref in all_refs if ref["target"] not in ids]
    assets = []
    for filename in dict.fromkeys(
        element.attrib["gfname"]
        for element in root.iter()
        if "gfname" in element.attrib
    ):
        asset_path = xml_path.parent / filename
        assets.append(
            {
                "file": relative_path(asset_path),
                "exists": asset_path.is_file(),
                "sha256": sha256(asset_path) if asset_path.is_file() else None,
            }
        )
    units, covered_langs = make_units(
        root,
        parents,
        paths,
        section_by_element,
        pmda_key,
        pmda_url,
        doc_meta["products"],
    )
    section_langs = {
        element
        for child in root
        if tag_name(child) not in catalog.xml.header_tags
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
        if text_of(element)
        and not any(text_of(element) in unit_text for unit_text in unit_texts)
    ]
    document = {
        "schema_version": "medi-chat.pmda-prescription-xml.v1",
        "source": {
            "file": relative_path(xml_path),
            "sha256": source_sha256,
            "namespace": namespace,
            "pmda_url": pmda_url,
            "figures": assets,
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
            if tag_name(child) in catalog.xml.header_tags
        ],
        "section_index": sections,
        "sections": [
            {
                "code": sec["code"],
                "title": sec["title"],
                "xml_id": sec.get("xml_id"),
                "xml_path": sec.get("xml_path", paths.get(element, "")),
                "tree": source_node(element),
            }
            for element, sec in section_by_element.items()
        ],
    }
    validation = {
        "source_file": relative_path(xml_path),
        "document_key": pmda_key,
        "xml_element_count": sum(1 for _ in root.iter()),
        "processing_instruction_count": sum(
            tag_name(element) == "#processing_instruction" for element in root.iter()
        ),
        "xml_lang_count": sum(tag_name(element) == "Lang" for element in root.iter()),
        "section_lang_count": len(section_langs),
        "covered_section_lang_count": len(section_langs & covered_langs),
        "uncovered_section_lang_paths": sorted(uncovered),
        "unrepresented_nonempty_lang_paths": sorted(unrepresented_text),
        "section_count": len(sections),
        "search_schema_version": "medi-chat.pmda-sections.v2",
        "search_unit_count": len(units),
        "search_unit_types": dict(Counter(unit["kind"] for unit in units)),
        "duplicate_section_codes": duplicate_section_codes,
        "duplicate_unit_ids": duplicate_unit_ids,
        "reference_count": len(all_refs),
        "unresolved_references": unresolved_refs,
        "missing_figures": [asset["file"] for asset in assets if not asset["exists"]],
        "status": "pass"
        if not uncovered
        and not duplicate_section_codes
        and not duplicate_unit_ids
        and not unrepresented_text
        and not unresolved_refs
        and all(asset["exists"] for asset in assets)
        else "fail",
        "notes": [
            "項目番号は医療用医薬品の記載要領に対応する明示的なタグ表で付与した。",
            "原文の解釈や禁忌判定は生成していない。検索単位は原文階層からの派生データ。",
            "XSDによる妥当性検証とPMDA表示との差分照合は未実施。",
        ],
    }
    if validation["status"] != "pass":
        raise ValueError(f"Transformation failed validation: {validation}")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "document.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (output_dir / "search_units.jsonl").open(
        "w", encoding="utf-8", newline="\n"
    ) as stream:
        for unit in units:
            stream.write(json.dumps(unit, ensure_ascii=False) + "\n")
    (output_dir / "validation.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return validation
