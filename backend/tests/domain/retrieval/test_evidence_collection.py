"""DM-09–13: 同一条件順の根拠内容・由来・項目順を固定する。"""

from copy import deepcopy

import pytest
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.medicine.identifiers import YjCode
from backend.domain.retrieval.identifiers import SearchUnitId
from backend.domain.retrieval.primitives import (
    DetectionSource,
    EvidenceExcerpt,
    EvidenceGenericName,
    EvidenceProductName,
    EvidenceSourceUrl,
    SearchUnitKind,
)
from backend.domain.retrieval.services import merge_evidence
from backend.domain.retrieval.value_objects import (
    DocumentRevision,
    Evidence,
    EvidenceColumns,
    EvidenceReference,
    EvidenceSection,
)


def make_evidence(unit_id="unit", code="11.1", excerpt="原文\n本文", **kwargs):
    data = {
        "unit_id": unit_id,
        "document_id": "document",
        "product_name": "商品",
        "generic_name": "成分",
        "product_yj_codes": ["1234567A0000"],
        "document_revision": {"date": "2026-10-03", "extra": {"value": [None]}},
        "section": {"code": code, "title": "原見出し"},
        "kind": "text",
        "excerpt": excerpt,
        "references": [{"url": "https://example.test/reference"}],
        "url": "https://example.test/document",
    }
    data.update(kwargs)
    columns = data.get("columns")
    retrieved_by = data.get("retrieved_by")
    return Evidence(
        unit_id=SearchUnitId.from_value(data["unit_id"]),
        document_id=DocumentId.from_value(data["document_id"]),
        product_name=EvidenceProductName(data["product_name"])
        if data["product_name"]
        else None,
        generic_name=EvidenceGenericName(data["generic_name"])
        if data["generic_name"]
        else None,
        product_yj_codes=tuple(
            YjCode.from_value(code) for code in data["product_yj_codes"]
        ),
        document_revision=DocumentRevision(data["document_revision"]),
        section=EvidenceSection(data["section"]),
        kind=SearchUnitKind(data["kind"]) if data["kind"] else None,
        excerpt=EvidenceExcerpt(data["excerpt"]),
        url=EvidenceSourceUrl(data["url"]) if data["url"] else None,
        columns=EvidenceColumns(columns) if columns is not None else None,
        references=tuple(EvidenceReference(ref) for ref in data.get("references", ())),
        retrieved_by=frozenset({DetectionSource(retrieved_by)})
        if retrieved_by is not None
        else frozenset(),
    )


async def collect(hits, order):
    return merge_evidence((hits[source], DetectionSource(source)) for source in order)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("order", "label"),
    [
        (("logic",), frozenset({"logic"})),
        (("jev",), frozenset({"jev"})),
        (("keyword",), frozenset({"keyword"})),
        (("logic", "jev"), frozenset(["logic", "jev"])),
        (("logic", "keyword"), frozenset(["logic", "keyword"])),
        (("jev", "keyword"), frozenset(["jev", "keyword"])),
        (("logic", "jev", "keyword"), frozenset(["logic", "jev", "keyword"])),
    ],
)
async def test_detection_labels_merge_without_mutating_input(order, label):
    original = make_evidence()
    before = deepcopy(original)
    result = await collect({source: [original, original] for source in order}, order)
    assert len(result) == 1
    assert result[0].retrieved_by == label
    assert original == before
    public = result[0].to_dict()
    public_revision = public["document_revision"]
    assert isinstance(public_revision, dict)
    public_revision["date"] = "changed"
    assert original == before


@pytest.mark.asyncio
async def test_distinct_ids_and_all_forty_evidences_are_retained():
    hits = [make_evidence(f"unit-{index:02}") for index in range(40)]
    result = await collect({"logic": [*hits, hits[0]]}, ("logic",))
    assert [item.unit_id.value for item in result] == [
        f"unit-{index:02}" for index in range(40)
    ]
    assert all(item.excerpt.value == "原文\n本文" for item in result)


def test_evidence_rejects_empty_unit_id():
    from backend.domain.foundation.exceptions import DomainValidationError

    with pytest.raises(DomainValidationError):
        make_evidence("")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("codes", "expected"),
    [
        (
            ["16.7", "10.2", "1", "3.2", "10", "2", "3.1"],
            ["1", "2", "3.1", "3.2", "10", "10.2", "16.7"],
        ),
        (["11.1", "9.5", "10.1", "9.4"], ["9.4", "9.5", "10.1", "11.1"]),
    ],
)
async def test_numeric_sections_and_unit_ids_define_order(codes, expected):
    hits = [make_evidence(f"z-{code}", code) for code in codes]
    hits.append(make_evidence("a", expected[0]))
    result = await collect({"logic": hits}, ("logic",))
    assert [item.section["code"] for item in result] == [expected[0], *expected]
    assert result[0].unit_id.value == "a"


@pytest.mark.asyncio
@pytest.mark.parametrize("order", [("logic", "jev"), ("jev", "logic")])
async def test_id_collision_keeps_first_content_for_each_condition_order(order):
    hits = {
        "logic": [make_evidence(excerpt="固定判定の原文")],
        "jev": [make_evidence(excerpt="Jevの原文")],
    }
    result = await collect(hits, order)
    assert len(result) == 1
    assert (
        result[0].excerpt.value
        == {"logic": "固定判定の原文", "jev": "Jevの原文"}[order[0]]
    )
    assert result[0].retrieved_by == frozenset(["logic", "jev"])


def test_merge_results_are_independent_snapshots():
    original = make_evidence(excerpt="最初の原文")
    batches = [([original], DetectionSource.LOGIC)]
    first = merge_evidence(batches)
    batches.append(([make_evidence(excerpt="後続の原文")], DetectionSource.KEYWORD))
    current = merge_evidence(batches)
    assert isinstance(first, tuple)
    assert first[0].retrieved_by == frozenset({"logic"})
    assert current[0].retrieved_by == frozenset(["logic", "keyword"])
    assert current[0].excerpt.value == "最初の原文"
    assert original.retrieved_by == frozenset()
    assert merge_evidence(()) == ()


@pytest.mark.parametrize(
    "order",
    [
        ("logic", "keyword", "jev"),
        ("jev", "logic", "keyword"),
        ("jev", "keyword", "logic"),
        ("keyword", "logic", "jev"),
        ("keyword", "jev", "logic"),
    ],
)
def test_all_three_detection_sources_merge_independently_of_order(order):
    result = merge_evidence(
        ([make_evidence()], DetectionSource(source)) for source in order
    )
    assert result[0].retrieved_by == frozenset(["logic", "jev", "keyword"])
    assert result[0].to_dict()["retrieved_by"] == [
        "logic",
        "jev",
        "keyword",
    ]


def test_missing_detection_sources_are_an_empty_public_array():
    assert make_evidence().retrieved_by == frozenset()
    assert make_evidence().to_dict()["retrieved_by"] == []


def test_merge_orders_numbered_then_text_then_missing_sections():
    hits = tuple(
        make_evidence(code or "missing", code)
        for code in ("", "appendix", "10", "2", "2.1")
    )
    result = merge_evidence(((hits, DetectionSource.LOGIC),))
    assert [item.section["code"] for item in result] == [
        "2",
        "2.1",
        "10",
        "appendix",
        "",
    ]


def test_merge_preserves_existing_sources_on_first_and_duplicate_hits():
    first = make_evidence(excerpt="最初", retrieved_by="logic")
    later = make_evidence(excerpt="後続", retrieved_by="keyword")
    result = merge_evidence((((first, later), DetectionSource.JEV),))
    assert result[0].retrieved_by == frozenset(DetectionSource)
    assert result[0].excerpt.value == "最初"
    assert first.retrieved_by == frozenset({DetectionSource.LOGIC})
    assert merge_evidence(((result, DetectionSource.LOGIC),)) == result
