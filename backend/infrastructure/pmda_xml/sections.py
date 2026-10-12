"""Fixed PMDA section numbers and XML section lookup."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from ..package_insert_definitions.loader import get_package_insert_definitions
from .definition_settings import PmdaXmlSettings
from .xml_nodes import tag_name


def section_definition(
    element: ET.Element,
    parents: dict[ET.Element, ET.Element],
    *,
    xml_settings: PmdaXmlSettings | None = None,
) -> tuple[str, str] | None:
    """Return the fixed section represented by a typed or contextual XML node."""
    if xml_settings is None:
        xml_settings = get_package_insert_definitions().xml_settings
    name = tag_name(element)
    definition = xml_settings.sections_by_xml_tag.get(name)
    if definition is not None:
        return definition.code, definition.title

    parent = parents.get(element)
    if parent is None:
        return None
    ancestor = parent
    while ancestor is not None:
        ancestor_name = tag_name(ancestor)
        definition = xml_settings.sections_by_xml_context.get((ancestor_name, name))
        if definition is not None:
            return definition.code, definition.title

        if ancestor_name in xml_settings.sections_by_xml_tag:
            return None
        ancestor = parents.get(ancestor)
    return None


def make_section_index(
    root: ET.Element,
    parents: dict[ET.Element, ET.Element],
    paths: dict[ET.Element, str],
    pmda_url: str,
    *,
    xml_settings: PmdaXmlSettings | None = None,
) -> tuple[list[dict[str, Any]], dict[ET.Element, dict[str, Any]]]:
    index = []
    by_element = {}
    for element in root.iter():
        name = tag_name(element)
        definition = section_definition(element, parents, xml_settings=xml_settings)
        if definition is None:
            continue
        code, title = definition
        parent = parents.get(element)
        ancestor = parent
        while ancestor is not None and ancestor not in by_element:
            ancestor = parents.get(ancestor)
        xml_id = element.attrib.get("id")
        record = {
            "code": code,
            "title": title,
            "xml_tag": name,
            "xml_id": xml_id,
            "parent_code": by_element[ancestor]["code"]
            if ancestor is not None
            else None,
            "xml_path": paths[element],
            "url": f"{pmda_url}#{xml_id}" if xml_id else pmda_url,
        }
        index.append(record)
        by_element[element] = record
    return index, by_element


def nearest_section(
    element: ET.Element,
    parents: dict[ET.Element, ET.Element],
    section_by_element: dict[ET.Element, dict[str, Any]],
) -> dict[str, Any]:
    current: ET.Element | None = element
    while current is not None:
        if current in section_by_element:
            return section_by_element[current]
        current = parents.get(current)
    raise ValueError(f"No numbered section for {tag_name(element)}")


def reference_section_code(
    element: ET.Element,
    parents: dict[ET.Element, ET.Element],
    section_by_element: dict[ET.Element, dict[str, Any]],
    *,
    xml_settings: PmdaXmlSettings | None = None,
) -> str:
    """Resolve ordered child targets without adding child search units.

    Legacy v2 section/fragment generation retains its existing representation.
    Typed references preserve the original numbered destination within a section.
    """
    section = nearest_section(element, parents, section_by_element)

    def list_scope(ordered: ET.Element) -> ET.Element:
        owner = parents[ordered]
        container = parents.get(owner)
        # SimpleList Item groups carry headings, while their numbered lists
        # continue within the shared container. A numbered Item owns its own
        # nested numbering and must not inherit another parent's count.
        if (
            tag_name(owner) == "Item"
            and container is not None
            and tag_name(container) == "SimpleList"
        ):
            return container
        return owner

    def item_number(item: ET.Element, ordered: ET.Element) -> int:
        scope = list_scope(ordered)
        offset = 0
        for candidate in scope.iter():
            if (
                tag_name(candidate) != "OrderedList"
                or list_scope(candidate) is not scope
            ):
                continue
            if nearest_section(candidate, parents, section_by_element) is not section:
                continue
            if candidate.attrib.get("numberContinued") != "true":
                offset = 0
            items = [child for child in candidate if tag_name(child) == "Item"]
            if candidate is ordered:
                return offset + items.index(item) + 1
            offset += len(items)
        raise ValueError("Numbered item is outside its list scope")

    suffix = []
    current: ET.Element | None = element
    while current is not None and current not in section_by_element:
        parent = parents.get(current)
        if (
            tag_name(current) == "Item"
            and parent is not None
            and tag_name(parent) == "OrderedList"
        ):
            suffix.append(str(item_number(current, parent)))
        current = parent
    return ".".join((section["code"], *reversed(suffix)))
