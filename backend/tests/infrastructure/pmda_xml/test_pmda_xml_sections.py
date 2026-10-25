"""SX-R09/R10: original XML and independent continued-number boundaries."""

import xml.etree.ElementTree as ET

import pytest
from backend.infrastructure.pmda_xml.section_mapping import (
    make_section_index,
    reference_section_code,
)
from backend.project_paths import PROJECT_ROOT


def resolve_targets(root, identifiers):
    parents = {child: parent for parent in root.iter() for child in parent}
    _, sections = make_section_index(
        root, parents, dict.fromkeys(root.iter(), ""), "https://example.invalid"
    )
    by_id = {node.attrib["id"]: node for node in root.iter() if "id" in node.attrib}
    return {
        identifier: reference_section_code(by_id[identifier], parents, sections)
        for identifier in identifiers
    }


@pytest.mark.source_data
@pytest.mark.parametrize(
    ("identifier", "expected"),
    [
        ("HDR_ContraIndications_1", "2.1"),
        ("HDR_ContraIndications_11", "2.11"),
        ("HDR_ContraIndications_12", "2.12"),
        ("HDR_ContraIndications_13", "2.13"),
        ("HDR_PediatricUse_1", "9.7.1"),
        ("HDR_PediatricUse_2", "9.7.2"),
    ],
)
def test_sx_r09_original_xml_continued_reference(identifier, expected):
    source = next(
        (PROJECT_ROOT / "data/pmda/originals").glob("*/630004_3339003F5020_1_08.xml")
    )
    root = ET.parse(source).getroot()
    assert resolve_targets(root, [identifier]) == {identifier: expected}


@pytest.mark.parametrize("boolean_one", ["true", "1"])
def test_sx_r10_continued_reset_nested_parent_and_section_boundaries(boolean_one):
    root = ET.fromstring("""
      <PackIns>
        <ContraIndications><SimpleList>
          <Item><OrderedList numberContinued="false">
            <Item id="a"><OrderedList><Item id="a1"/><Item id="a2"/></OrderedList>
              <OrderedList numberContinued="true"><Item id="a3"/></OrderedList></Item>
            <Item id="b"><OrderedList numberContinued="true"><Item id="b1"/></OrderedList></Item>
          </OrderedList></Item>
          <Item><OrderedList numberContinued="true"><Item id="c"/><Item id="d"/></OrderedList></Item>
          <Item><OrderedList numberContinued="false"><Item id="e"/></OrderedList></Item>
          <Item><OrderedList numberContinued="true"><Item id="f"/></OrderedList></Item>
        </SimpleList>
        <Detail><OrderedList numberContinued="true"><Item id="other_parent"/></OrderedList></Detail>
        </ContraIndications>
        <Warnings><OrderedList numberContinued="true"><Item id="other_section"/></OrderedList></Warnings>
      </PackIns>
    """)
    if boolean_one == "1":
        root = ET.fromstring(
            ET.tostring(root).replace(b'numberContinued="true"', b'numberContinued="1"')
        )
    expected = {
        "a": "2.1",
        "b": "2.2",
        "c": "2.3",
        "d": "2.4",
        "e": "2.1",
        "f": "2.2",
        "a1": "2.1.1",
        "a2": "2.1.2",
        "a3": "2.1.3",
        "b1": "2.2.1",
        "other_parent": "2.1",
        "other_section": "1.1",
    }
    assert resolve_targets(root, expected) == expected
