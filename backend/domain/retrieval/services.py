"""検索コンテキストの状態を持たないDomain Service。"""

from collections.abc import Iterable, Sequence
from dataclasses import replace
from typing import Protocol

from ..medicine.identifiers import YjCode
from ..shared.services import normalize_match_text
from .entities import SearchUnit
from .identifiers import SearchUnitId
from .primitives import (
    DetectionSource,
    EvidenceContextLabel,
    IntentName,
    Probability,
    SearchSectionCode,
)
from .value_objects import (
    Evidence,
    EvidenceDocument,
    IntentCandidate,
    IntentPolicy,
    IntentSelection,
    SearchCriteria,
    SearchUnitCriteria,
    TextSearchPolicy,
)


def detect_intent_from_keywords(message: str, *, intent_policy: IntentPolicy) -> str:
    """最初の一致を採用し、一致がなければ通常検索の意図を返す。"""
    compact = normalize_match_text(message)
    for definition in intent_policy.keyword_intents:
        if any(
            normalize_match_text(keyword.text) in compact
            for keyword in definition.keywords
        ):
            return definition.id.value
    return intent_policy.fallback_intent.value


def detect_fixed_keyword_criteria(
    message: str, intent_policy: IntentPolicy
) -> SearchCriteria | None:
    """項目指定のない意図は固定項目検索の条件にしない。"""
    intent = detect_intent_from_keywords(message, intent_policy=intent_policy)
    codes = intent_policy.section_codes_for_intent(intent)
    if not codes:
        return None
    return SearchCriteria(
        source=DetectionSource.LOGIC,
        intent=IntentName(intent),
        section_codes=tuple(SearchSectionCode(code) for code in codes),
    )


_DEFAULT_INTENT_THRESHOLD = Probability(0.20)


def select_intents(
    candidates: tuple[IntentCandidate, ...],
    choice: str | None,
    *,
    intent_policy: IntentPolicy,
    baseline_intent: str | None = None,
    threshold: Probability = _DEFAULT_INTENT_THRESHOLD,
) -> IntentSelection:
    if baseline_intent is None:
        baseline_intent = intent_policy.fallback_intent.value
    qualifying = tuple(
        candidate.intent.value
        for candidate in sorted(
            (
                candidate
                for candidate in candidates
                if candidate.probability.value >= threshold.value
                and candidate.intent.value != intent_policy.general_intent.value
            ),
            key=lambda item: item.probability.value,
            reverse=True,
        )
    )
    if not qualifying and choice and choice != intent_policy.general_intent.value:
        qualifying = (choice,)
    sections = tuple(
        dict.fromkeys(
            code
            for intent in qualifying
            for code in intent_policy.section_codes_for_intent(intent)
        )
    )
    primary = (
        qualifying[0]
        if qualifying
        else choice
        if choice == intent_policy.general_intent.value
        else baseline_intent
    )
    return IntentSelection(
        primary=IntentName(primary) if primary is not None else None,
        qualifying_intents=tuple(IntentName(intent) for intent in qualifying),
        section_codes=tuple(SearchSectionCode(code) for code in sections),
    )


def build_evidence(
    unit: Evidence,
    document: EvidenceDocument,
    context_labels: tuple[EvidenceContextLabel, ...],
) -> Evidence:
    """検索単位に原本の製品名・一般名・文脈を組み合わせる。"""
    selected = select_products(document.products, unit.product_yj_codes)
    brand_names = tuple(
        dict.fromkeys(
            product.brand_name.value
            for product in selected
            if product.brand_name is not None
        )
    )
    generic_name = (
        document.generic_name.value if document.generic_name is not None else ""
    )
    return replace(
        unit,
        product_name=" / ".join(brand_names) or generic_name or unit.document_id.value,
        generic_name=generic_name,
        excerpt=format_scoped_text(
            unit.excerpt, tuple(label.value for label in context_labels)
        ),
        url=unit.url
        or (document.pmda_url.value if document.pmda_url is not None else ""),
    )


def select_units(
    units: Iterable[SearchUnit],
    criteria: SearchUnitCriteria,
) -> tuple[SearchUnit, ...]:
    """検索単位を項目・製品条件で絞り、入力順を保った結果を返す。"""
    selected: list[SearchUnit] = []
    section_codes = {code.value for code in criteria.section_codes}
    product_codes = criteria.product_codes
    for unit in units:
        if section_codes and unit.section_code.value not in section_codes:
            continue
        if product_codes and not product_codes.intersection(unit.product_codes):
            continue
        selected.append(unit)
    return tuple(selected)


class ProductIdentity(Protocol):
    @property
    def yj_code(self) -> YjCode | None: ...


def select_products[T: ProductIdentity](
    products: tuple[T, ...], codes: tuple[YjCode, ...]
) -> tuple[T, ...]:
    """指定コードに一致する製品を選び、該当がなければ全製品を返す。"""
    requested = frozenset(codes)
    selected = tuple(product for product in products if product.yj_code in requested)
    return selected or products


def is_scope_heading_only(
    kind: str | None, text: str, *, text_search_policy: TextSearchPolicy
) -> bool:
    """本文が検索範囲見出しだけか判定する。"""
    return kind == "item" and text.strip() in text_search_policy.scope_heading_texts


def evidence_section_sort_key(
    evidence: Evidence,
) -> tuple[tuple[tuple[int, int | str], ...], str]:
    """根拠を番号・文字列・空項目の順、同項目はID順に並べるキー。"""
    parts = section_code_sort_key(evidence.section.get("code") or "")
    # 数値、文字列、空値の順に型を揃えて比較する。
    return tuple(
        (0, part) if isinstance(part, int) else (1 if part else 2, part)
        for part in parts
    ), evidence.unit_id.value


def merge_evidence(
    batches: Iterable[tuple[Iterable[Evidence], DetectionSource]],
) -> tuple[Evidence, ...]:
    """同じ検索単位の最初の原文を保持し、取得経路を統合して項目順に返す。"""
    hits: dict[SearchUnitId, tuple[Evidence, set[DetectionSource]]] = {}
    for evidences, source in batches:
        for evidence in evidences:
            if evidence.unit_id not in hits:
                hits[evidence.unit_id] = (
                    evidence,
                    set(evidence.retrieved_by) | {source},
                )
            else:
                hits[evidence.unit_id][1].update(evidence.retrieved_by | {source})
    return tuple(
        sorted(
            (
                replace(evidence, retrieved_by=frozenset(sources))
                for evidence, sources in hits.values()
            ),
            key=evidence_section_sort_key,
        )
    )


def section_code_sort_key(code: str) -> tuple[int | str, ...]:
    return tuple(int(part) if part.isdigit() else part for part in code.split("."))


def format_scoped_text(text: str, scope: Sequence[str]) -> str:
    missing = [label for label in scope if label not in text]
    if not missing:
        return text
    labels = [
        label if label.startswith(("〈", "＜", "［", "[")) else f"〈{label}〉"
        for label in missing
    ]
    prefix = " ".join(labels)
    return f"{prefix}\n{text}" if "\n" in text or len(text) > 40 else f"{prefix} {text}"
