"""Build version-bound search units from the preserved XML tree."""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from typing import Any

from backend.application.indexing.queries.policies.text_projection import (
    format_scoped_text,
)

from ..package_insert_definitions.assembly import get_package_insert_definitions
from .definition_settings import PmdaXmlSettings
from .sections import nearest_section
from .xml_nodes import (
    direct_child,
    tag_name,
    text_lines,
    text_of,
)


def context_labels(
    element: ET.Element,
    parents: dict[ET.Element, ET.Element],
    *,
    xml_settings: PmdaXmlSettings | None = None,
) -> list[str]:
    labels = []
    current = parents.get(element)
    while current is not None:
        if tag_name(current) == "Item":
            header = direct_child(current, "Header")
            label = text_of(header, xml_settings=xml_settings)
            if label:
                labels.append(label)
        current = parents.get(current)
    return list(reversed(labels))


def _referenced_products(
    element: ET.Element, products_by_id: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    reference = element.attrib.get("brandRef") or element.attrib.get("productRef")
    if not reference:
        return []
    return [
        products_by_id[product_id]
        for product_id in re.split(r"[\s,]+", reference)
        if product_id in products_by_id
    ]


def _scoped_products(
    element: ET.Element,
    parts: list[ET.Element],
    parents: dict[ET.Element, ET.Element],
    products: list[dict[str, Any]],
    products_by_id: dict[str, dict[str, Any]],
    scope: list[str],
) -> list[dict[str, Any]]:
    """Prefer explicit product references, then labels, then document products."""
    current: ET.Element | None = element
    while current is not None:
        matched = _referenced_products(current, products_by_id)
        if matched:
            return matched
        current = parents.get(current)

    for part in parts:
        for child in part.iter():
            matched = _referenced_products(child, products_by_id)
            if matched:
                return matched

    if len(products) > 1:
        matched = [
            product
            for product in products
            if product.get("brand_name")
            and any(product["brand_name"] in label for label in scope)
        ]
        if matched:
            return matched
    return products


def _make_fragments(
    root: ET.Element,
    parents: dict[ET.Element, ET.Element],
    paths: dict[ET.Element, str],
    section_by_element: dict[ET.Element, dict[str, Any]],
    pmda_url: str,
    products: list[dict[str, Any]],
    *,
    xml_settings: PmdaXmlSettings | None = None,
) -> tuple[list[dict[str, Any]], set[ET.Element]]:
    if xml_settings is None:
        xml_settings = get_package_insert_definitions().xml_settings
    products_by_id = {p["xml_id"]: p for p in products if p.get("xml_id")}
    ids = {
        element.attrib["id"]: element
        for element in root.iter()
        if "id" in element.attrib
    }
    labels = {
        key: text_of(element, xml_settings=xml_settings)
        for key, element in ids.items()
        if tag_name(element) in {"Category", "Frequency"}
    }
    referenced_labels = {
        element.attrib[name]
        for element in root.iter()
        for name in ("categoryRef", "frequencyRef")
        if name in element.attrib
    }
    units: list[dict[str, Any]] = []
    covered_langs: set[ET.Element] = set()

    def emit(
        element: ET.Element, kind: str, parts: list[ET.Element] | None = None
    ) -> None:
        parts = parts or [element]
        section = nearest_section(element, parents, section_by_element)
        langs = [
            child
            for part in parts
            for child in part.iter()
            if tag_name(child) == "Lang"
        ]
        covered_langs.update(langs)
        texts = [text_of(part, xml_settings=xml_settings) for part in parts]
        texts = [value for value in texts if value]
        text = "\n".join(texts)
        attributes = element.attrib
        extra: dict[str, Any] = {}
        if kind == "interaction_row":
            extra["columns"] = {
                column.id: "\n".join(
                    text_lines(
                        direct_child(element, column.xml_tag), xml_settings=xml_settings
                    )
                )
                for column in xml_settings.interaction_columns
            }
            text = "\n".join(
                f"{name}: {value}" for name, value in extra["columns"].items() if value
            )
        elif kind == "adverse_reaction_cell":
            category_id = attributes.get("categoryRef")
            frequency_id = attributes.get("frequencyRef")
            category_label = labels.get(category_id) if category_id else None
            frequency_label = labels.get(frequency_id) if frequency_id else None
            extra["category"] = {
                "xml_id": category_id,
                "label": category_label,
            }
            extra["frequency"] = {
                "xml_id": frequency_id,
                "label": frequency_label,
            }
        elif kind == "table_row":
            cells = [child for child in element if tag_name(child) == "SimpTblCell"]
            extra["cells"] = [
                {
                    "text": "\n".join(text_lines(cell, xml_settings=xml_settings)),
                    "attributes": dict(cell.attrib),
                }
                for cell in cells
            ]
            table = parents.get(element)
            if table is not None:
                rows = [child for child in table if tag_name(child) == "SimpTblRow"]
                extra["row_index_zero_based"] = rows.index(element)
                extra["table_xml_path"] = paths[table]
            text = " | ".join(cell["text"] for cell in extra["cells"])
        elif kind == "graphic":
            filenames = list(
                dict.fromkeys(
                    child.attrib["gfname"]
                    for child in element.iter()
                    if "gfname" in child.attrib
                )
            )
            captions = [
                text_of(child, xml_settings=xml_settings)
                for child in element.iter()
                if tag_name(child) == "GraphicCaption"
                and text_of(child, xml_settings=xml_settings)
            ]
            extra["figure_captions"] = captions
            text = "\n".join(
                part
                for part in [
                    "図ファイル: " + ", ".join(filenames) if filenames else "",
                    *["図の説明: " + caption for caption in captions],
                ]
                if part
            )
        if not text and not langs and kind != "graphic":
            return
        referenced = []
        seen_refs = set()
        for part in parts:
            for child in part.iter():
                if tag_name(child) not in xml_settings.reference_tags:
                    continue
                target_id = child.attrib.get("ref")
                key = (tag_name(child), target_id)
                if key in seen_refs:
                    continue
                seen_refs.add(key)
                target = ids.get(target_id) if target_id else None
                referenced.append(
                    {
                        "kind": tag_name(child),
                        "target_xml_id": target_id,
                        "target_xml_path": paths[target]
                        if target is not None
                        else None,
                        "target_section_code": (
                            nearest_section(target, parents, section_by_element)["code"]
                            if target is not None
                            else None
                        ),
                        "target_url": f"{pmda_url}#{target_id}" if target_id else None,
                    }
                )
        scope = context_labels(element, parents, xml_settings=xml_settings)

        scoped_products = _scoped_products(
            element,
            [] if kind == "table_row" else parts,
            parents,
            products,
            products_by_id,
            scope,
        )

        unit_yj_codes = [p["yj_code"] for p in scoped_products if p.get("yj_code")]
        unit: dict[str, Any] = {
            "product_yj_codes": unit_yj_codes,
            "kind": kind,
            "section": {"code": section["code"], "title": section["title"]},
            "text": text,
            "context_labels": scope,
            "references": referenced,
        }
        unit.update(extra)
        units.append(unit)

    def visit(element: ET.Element) -> None:
        name = tag_name(element)
        if (
            name in {"Category", "Frequency"}
            and element.attrib.get("id") in referenced_labels
        ):
            # These labels are rendered with their cells; do not repeat them as prose.
            covered_langs.update(
                child for child in element.iter() if tag_name(child) == "Lang"
            )
            return
        if name in xml_settings.atomic_units:
            emit(element, xml_settings.atomic_units[name])
            return
        if name in {"Detail", "Header", "Lang"}:
            emit(element, name.lower())
            return
        for child in element:
            visit(child)

    for section in root:
        if tag_name(section) not in xml_settings.header_tags:
            visit(section)
    return units, covered_langs


def _table_row(
    values: list[str],
    attributes: list[dict[str, Any]] | None = None,
    *,
    xml_settings: PmdaXmlSettings | None = None,
) -> str:
    cells = []
    for index, value in enumerate(values):
        attrs = attributes[index] if attributes is not None else {}
        spans = "".join(
            f' {target}="{int(attrs[source])}"'
            for source, target in (("rspan", "rowspan"), ("cspan", "colspan"))
            if source in attrs
        )
        cells.append(
            f'<td{spans} style="white-space: pre-wrap">{html.escape(value)}</td>'
        )
    return "<tr>" + "".join(cells) + "</tr>"


def _render_section(
    fragments: list[dict[str, Any]],
    products: list[dict[str, Any]],
    *,
    xml_settings: PmdaXmlSettings | None = None,
) -> str:
    """Keep product scopes, captions and table relationships in a single body."""
    if xml_settings is None:
        xml_settings = get_package_insert_definitions().xml_settings
    names = {
        product.get("yj_code"): product.get("brand_name", "") for product in products
    }
    blocks: list[str] = []
    last_table: str | None = None
    last_codes: tuple[str, ...] | None = None
    last_scope: tuple[str, ...] | None = None
    for fragment in fragments:
        codes = tuple(fragment["product_yj_codes"])
        if len(products) > 1 and codes != last_codes:
            labels = [f"{names.get(code, '')} [YJ: {code}]" for code in codes]
            blocks.append("### 対象製品: " + " / ".join(labels))
            last_table = None
        last_codes = codes
        scope = tuple(fragment["context_labels"])
        if scope != last_scope:
            if scope:
                blocks.append("### " + format_scoped_text("", scope).strip())
            last_table = None
        last_scope = scope
        kind = fragment["kind"]
        headings = ""
        table_key = None
        row = ""
        if kind == "interaction_row":
            headings = _table_row(
                [column.title for column in xml_settings.interaction_columns],
                xml_settings=xml_settings,
            )
            row = _table_row(
                [
                    fragment["columns"][column.id]
                    for column in xml_settings.interaction_columns
                ],
                xml_settings=xml_settings,
            )
            table_key = kind
        elif kind == "adverse_reaction_cell":
            headings = _table_row(["分類", "頻度", "副作用"], xml_settings=xml_settings)
            row = _table_row(
                [
                    fragment["category"]["label"] or "",
                    fragment["frequency"]["label"] or "",
                    fragment["text"],
                ],
                xml_settings=xml_settings,
            )
            table_key = kind
        elif kind == "table_row":
            table_key = fragment["table_xml_path"]
            row = _table_row(
                [cell["text"] for cell in fragment["cells"]],
                [cell["attributes"] for cell in fragment["cells"]],
                xml_settings=xml_settings,
            )
        else:
            blocks.append(fragment["text"])
        if table_key is not None:
            if last_table == table_key:
                blocks[-1] = blocks[-1][:-8] + row + "</table>"
            else:
                blocks.append("<table>" + headings + row + "</table>")
        last_table = table_key
    return "\n\n".join(blocks)


def make_units(
    root: ET.Element,
    parents: dict[ET.Element, ET.Element],
    paths: dict[ET.Element, str],
    section_by_element: dict[ET.Element, dict[str, Any]],
    pmda_key: str,
    pmda_url: str,
    products: list[dict[str, Any]],
    *,
    xml_settings: PmdaXmlSettings | None = None,
) -> tuple[list[dict[str, Any]], set[ET.Element]]:
    """Emit one simple search record per numbered section with its own content."""
    fragments, covered = _make_fragments(
        root,
        parents,
        paths,
        section_by_element,
        pmda_url,
        products,
        xml_settings=xml_settings,
    )
    grouped: dict[str, list[dict[str, Any]]] = {}
    for fragment in fragments:
        grouped.setdefault(fragment["section"]["code"], []).append(fragment)
    definitions = {
        definition["code"]: definition for definition in section_by_element.values()
    }
    units = []
    for code, parts in grouped.items():
        references = []
        for part in parts:
            for reference in part["references"]:
                compact = {
                    key: reference[key]
                    for key in ("kind", "target_section_code", "target_url")
                }
                if compact not in references:
                    references.append(compact)
        units.append(
            {
                "unit_id": f"{pmda_key}:{code}",
                "document_key": pmda_key,
                "kind": "section",
                "section": parts[0]["section"],
                "product_yj_codes": list(
                    dict.fromkeys(
                        code for part in parts for code in part["product_yj_codes"]
                    )
                ),
                "text": _render_section(parts, products, xml_settings=xml_settings),
                "source": {"url": definitions[code]["url"]},
                "references": references,
            }
        )
    return units, covered
