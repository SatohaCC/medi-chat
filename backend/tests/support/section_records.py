"""保存形式の階層が変わっても原本レコードを独立に照合する。"""


def flatten_sections(sections):
    return [
        record
        for section in sections
        for record in (section, *flatten_sections(section.get("children", [])))
    ]


def assert_original_records_preserved(actual, expected):
    assert actual["schema_version"] == "medi-chat.pmda-prescription-xml.v2"
    assert {
        key: value
        for key, value in actual.items()
        if key not in {"sections", "schema_version"}
    } == {
        key: value
        for key, value in expected.items()
        if key not in {"sections", "schema_version"}
    }
    assert [
        {
            key: value
            for key, value in section.items()
            if key not in {"header", "children"}
        }
        for section in flatten_sections(actual["sections"])
    ] == expected["sections"]


def major_unit_id(document, code):
    return f"{document['document_id']}:{document['sha256']}:{code.split('.', 1)[0]}"
