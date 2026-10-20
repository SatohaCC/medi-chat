"""検索Primitiveの検証と型付きモデルの不変性。"""

from dataclasses import FrozenInstanceError, fields, replace
from typing import Any

import pytest
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.foundation.exceptions import DomainValidationError
from backend.domain.retrieval import primitives as p
from backend.domain.retrieval import value_objects as v
from backend.domain.retrieval.entities import SearchUnit
from backend.domain.retrieval.identifiers import SearchUnitId


@pytest.mark.parametrize(
    "kind,minimum",
    [(p.KeywordPriority, 1), (p.SearchColumnIndex, 0), (p.SearchCellSpan, 1)],
)
def test_numeric_primitives_enforce_integer_boundaries(kind, minimum):
    assert kind(minimum).value == minimum
    for invalid in [minimum - 1, True, False, 1.0, "1", None]:
        with pytest.raises(DomainValidationError):
            kind(invalid)


@pytest.mark.parametrize(
    "kind",
    [
        p.EvidenceProductName,
        p.EvidenceBrandName,
        p.EvidenceGenericName,
        p.EvidenceSourceUrl,
        p.SearchPolicyTerm,
    ],
)
def test_original_values_preserve_spelling_but_reject_blank(kind):
    raw = " テストＡ①\n"
    value = kind(raw)
    assert value.value == raw
    assert value == kind(raw)
    for invalid in ["", " \t　", None, False, 1, [], {}]:
        with pytest.raises(DomainValidationError):
            kind(invalid)
    with pytest.raises(FrozenInstanceError):
        value.value = "変更"


def test_excerpt_preserves_empty_original():
    assert p.EvidenceExcerpt("").value == ""
    assert p.EvidenceExcerpt(" \nＡ① ").value == " \nＡ① "
    with pytest.raises(DomainValidationError):
        p.EvidenceExcerpt(None)  # pyright: ignore[reportArgumentType]


def examples() -> list[Any]:
    context = v.SearchContentContext()
    cell = v.SearchTableCell(
        text=p.SearchUnitText(""),
        column=p.SearchColumnIndex(0),
        rowspan=p.SearchCellSpan(1),
        colspan=p.SearchCellSpan(1),
    )
    table = v.SearchTable(columns=(), rows=())
    fallback = v.SearchIntentDefinition(
        id=p.IntentName("other"), section_codes=(), keywords=(), keyword_priority=None
    )
    general = replace(fallback, id=p.IntentName("general"))
    return [
        v.IntentKeyword(
            text=p.IntentKeywordText("警告"), exclude_from_text_search=False
        ),
        fallback,
        v.IntentPolicy(
            intents=(fallback, general),
            fallback_intent=fallback.id,
            general_intent=general.id,
        ),
        v.SymptomKeywordRule(
            adjective=p.SearchPolicyTerm("眠い"), keywords=(p.SearchPolicyTerm("眠気"),)
        ),
        v.TextSearchPolicy(
            stop_words=frozenset(), symptom_rules=(), scope_heading_texts=frozenset()
        ),
        context,
        v.SearchContentReference(label=p.SearchUnitText("参照")),
        cell,
        table,
        v.SearchParagraph(text=p.SearchUnitText(""), context=context),
        v.SearchTableBlock(table=table, context=context),
        v.SearchFigure(
            reference=p.SearchUnitText("fig"),
            description=p.SearchUnitText(""),
            context=context,
        ),
        v.SearchCriteria(source=p.DetectionSource.LOGIC),
        v.IntentCandidate(p.IntentName("other"), p.Probability(0)),
        v.IntentSelection(),
        v.DocumentRevision({}),
        v.EvidenceReference({}),
        v.EvidenceSection({}),
        v.EvidenceColumns({}),
        v.EvidenceProduct(yj_code=None),
        v.EvidenceDocument(generic_name=None, products=()),
        v.Evidence(
            unit_id=SearchUnitId("unit"),
            document_id=DocumentId("doc"),
            product_name=None,
            generic_name=None,
            product_yj_codes=(),
            document_revision=v.DocumentRevision({}),
            section=v.EvidenceSection({}),
            kind=None,
            excerpt=p.EvidenceExcerpt(""),
            url=None,
        ),
        SearchUnit(
            unit_id=SearchUnitId("unit"),
            document_id=DocumentId("doc"),
            section_code=p.SearchUnitSectionCode("1"),
            kind=p.SearchUnitKind("section"),
            text=p.SearchUnitText(""),
        ),
    ]


MODELS = examples()


def test_models_are_frozen_and_defaults_are_valid():
    for model in MODELS:
        assert replace(model) == model
        with pytest.raises(FrozenInstanceError):
            setattr(model, fields(model)[0].name, None)


def test_evidence_public_empty_values_stay_basic_types():
    evidence = next(m for m in MODELS if isinstance(m, v.Evidence))
    payload = evidence.to_dict()
    assert all(
        payload[key] == ""
        for key in ("product_name", "generic_name", "kind", "excerpt", "url")
    )


def test_search_policy_does_not_retain_source_mapping_or_lists():
    raw = {"眠い": ["眠気", "傾眠"]}
    policy = v.TextSearchPolicy(
        stop_words=frozenset({p.SearchPolicyTerm("テスト除外語")}),
        symptom_rules=tuple(
            v.SymptomKeywordRule(
                adjective=p.SearchPolicyTerm(word),
                keywords=tuple(p.SearchPolicyTerm(term) for term in terms),
            )
            for word, terms in raw.items()
        ),
        scope_heading_texts=frozenset({p.SearchPolicyTerm("テスト見出し")}),
    )
    raw["眠い"].clear()
    raw.clear()
    assert tuple(term.value for term in policy.symptom_rules[0].keywords) == (
        "眠気",
        "傾眠",
    )
    with pytest.raises(FrozenInstanceError):
        policy.symptom_rules[0].keywords += ()  # pyright: ignore[reportAttributeAccessIssue]


def test_evidence_mappings_keep_empty_original_values_and_independent_output():
    raw = {"unknown": "", "code": "自由な番号"}
    section = v.EvidenceSection(raw)
    raw.clear()
    output = section.to_dict()
    output.clear()
    assert section.to_dict() == {"unknown": "", "code": "自由な番号"}
