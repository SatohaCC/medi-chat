"""Reader-port aggregation oracle, independent of storage projection granularity."""

import pytest
from backend.application.indexing.search_models import DocumentRevision
from backend.application.indexing.search_values import SearchUnitId, SearchUnitKind
from backend.application.retrieval.retrieve_evidence import _search_evidence
from backend.application.retrieval.search_models import (
    Evidence,
    EvidenceSection,
    SearchCriteria,
)
from backend.application.retrieval.search_values import (
    DetectionSource,
    EvidenceExcerpt,
    EvidenceGenericName,
    EvidenceProductName,
    EvidenceSourceUrl,
)
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.medicine.identifiers import YjCode


def evidence(index, code="11.1", text=None):
    return Evidence(
        unit_id=SearchUnitId(f"test_001:{index:03d}"),
        document_id=DocumentId("test_001"),
        product_name=EvidenceProductName("テスト薬"),
        generic_name=EvidenceGenericName("テスト成分"),
        product_yj_codes=(YjCode("1234567A0000"),),
        document_revision=DocumentRevision({}),
        section=EvidenceSection({"code": code, "title": "原見出し"}),
        kind=SearchUnitKind("text"),
        excerpt=EvidenceExcerpt(
            text if text is not None else f"頭痛に注意してください。記載{index}"
        ),
        url=EvidenceSourceUrl("https://example.test/package-insert"),
    )


class Batches:
    def __init__(self, values):
        self.values = values
        self.calls = []

    async def search(self, criteria, medicines):
        self.calls.append(criteria.source)
        return self.values[criteria.source]


@pytest.mark.asyncio
async def test_三種類の検索結果は件数を制限せず重複だけを除く():
    units = tuple(evidence(index) for index in range(40))
    reader = Batches(dict.fromkeys(DetectionSource, units))
    sources = await _search_evidence(
        reader, (), [SearchCriteria(source=source) for source in DetectionSource]
    )
    assert len(sources) == 40
    assert [source.unit_id.value for source in sources] == [
        f"test_001:{index:03d}" for index in range(40)
    ]
    assert {source.retrieved_by for source in sources} == {
        frozenset(["logic", "jev", "keyword"])
    }
    assert len(reader.calls) == 3


@pytest.mark.asyncio
async def test_重複はunit_idだけで除去し固有unitと取得元を保持する():
    units = (
        evidence(0, "1", "頭痛の同じ原文"),
        evidence(1, "10.1", "個別unitの同じ原文"),
        evidence(2, "16.7", "個別unitの同じ原文"),
        evidence(3, "11.1", "頭痛の同じ原文"),
    )
    reader = Batches(
        {
            DetectionSource.LOGIC: (units[0], units[1]),
            DetectionSource.JEV: (units[0], units[2]),
            DetectionSource.KEYWORD: (units[0], units[3]),
        }
    )
    sources = await _search_evidence(
        reader, (), [SearchCriteria(source=source) for source in DetectionSource]
    )
    assert len(sources) == 4
    assert {source.unit_id.value: source.retrieved_by for source in sources} == {
        "test_001:000": frozenset(["logic", "jev", "keyword"]),
        "test_001:001": frozenset({"logic"}),
        "test_001:002": frozenset({"jev"}),
        "test_001:003": frozenset({"keyword"}),
    }
    assert {source.unit_id.value: source.excerpt.value for source in sources} == {
        "test_001:000": "頭痛の同じ原文",
        "test_001:001": "個別unitの同じ原文",
        "test_001:002": "個別unitの同じ原文",
        "test_001:003": "頭痛の同じ原文",
    }
