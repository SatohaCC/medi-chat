"""構造化JSONから純粋な根拠・文書値へ変換する境界。"""

from dataclasses import dataclass

from ..domain.attachment.identifiers import DocumentId
from ..domain.json_types import JsonValue
from ..domain.medicine.identifiers import YjCode
from ..domain.retrieval.identifiers import SearchUnitId
from ..domain.retrieval.primitives import (
    DetectionSource,
    EvidenceBrandName,
    EvidenceContextLabel,
    EvidenceGenericName,
    EvidenceSourceUrl,
)
from ..domain.retrieval.services import (
    build_evidence as format_evidence,
)
from ..domain.retrieval.services import is_scope_heading_only as scope_heading_only
from ..domain.retrieval.services import select_products
from ..domain.retrieval.value_objects import (
    DocumentRevision,
    Evidence,
    EvidenceColumns,
    EvidenceDocument,
    EvidenceProduct,
    EvidenceReference,
    EvidenceSection,
    TextSearchPolicy,
)


def _object(value: JsonValue) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise TypeError("Expected a JSON object")
    return value


def _string(value: JsonValue) -> str:
    if not isinstance(value, str):
        raise TypeError("Expected a JSON string")
    return value


def _strings(value: JsonValue) -> list[str]:
    if not isinstance(value, list):
        raise TypeError("Expected a JSON array")
    return [_string(item) for item in value]


def _objects(value: JsonValue) -> list[dict[str, JsonValue]]:
    if not isinstance(value, list):
        raise TypeError("Expected a JSON array")
    return [_object(item) for item in value]


def _string_object(value: JsonValue) -> dict[str, str]:
    return {key: _string(item) for key, item in _object(value).items()}


def is_scope_heading_only(
    unit: dict[str, JsonValue], *, text_search_policy: TextSearchPolicy
) -> bool:
    kind = unit.get("kind")
    return scope_heading_only(
        kind if isinstance(kind, str) else None,
        _string(unit.get("text") or ""),
        text_search_policy=text_search_policy,
    )


def build_evidence(
    unit: dict[str, JsonValue],
    document_payload: dict[str, JsonValue],
    retrieved_by: DetectionSource | str,
) -> Evidence:
    document_id = _string(unit["document_key"])
    metadata = _object(document_payload.get("document") or {})
    products = _objects(metadata.get("products") or [])
    codes = tuple(YjCode(code) for code in _strings(unit.get("product_yj_codes") or []))
    selected = select_products(
        tuple(
            _ProductPayload(
                YjCode(_string(code))
                if (code := product.get("yj_code")) is not None
                else None,
                product,
            )
            for product in products
        ),
        codes,
    )
    unit_url = _object(unit.get("source") or {}).get("url")
    generic_name = _string(metadata.get("generic_name") or "")
    pmda_url = (
        _string(_object(document_payload.get("source") or {}).get("pmda_url") or "")
        if not unit_url
        else ""
    )
    document = EvidenceDocument(
        generic_name=EvidenceGenericName(generic_name) if generic_name else None,
        products=tuple(
            EvidenceProduct(
                yj_code=item.yj_code,
                brand_name=EvidenceBrandName(name)
                if (name := _string(item.payload.get("brand_name") or ""))
                else None,
            )
            for item in selected
        ),
        pmda_url=EvidenceSourceUrl(pmda_url) if pmda_url else None,
    )
    revision = unit.get("document_revision")
    if revision is None and unit.get("kind") == "section":
        revisions = _objects(metadata.get("revisions") or [])
        revision = next(
            (item for item in revisions if item.get("source_label") == "今回"),
            revisions[0] if revisions else {},
        )
    columns = unit.get("columns")
    raw_unit = Evidence(
        unit_id=SearchUnitId(_string(unit["unit_id"])),
        document_id=DocumentId(document_id),
        product_name="",
        generic_name="",
        product_yj_codes=codes,
        document_revision=DocumentRevision(_object(revision or {})),
        section=EvidenceSection(_string_object(unit.get("section") or {})),
        kind=_string(unit.get("kind") or ""),
        excerpt=_string(unit.get("text") or ""),
        columns=EvidenceColumns(_string_object(columns))
        if columns is not None
        else None,
        references=tuple(
            EvidenceReference(ref) for ref in _objects(unit.get("references") or [])
        ),
        url=_string(unit_url or ""),
        retrieved_by=frozenset({DetectionSource(retrieved_by)}),
    )
    return format_evidence(
        raw_unit,
        document,
        tuple(
            EvidenceContextLabel(label)
            for label in _strings(unit.get("context_labels") or [])
        ),
    )


@dataclass(frozen=True)
class _ProductPayload:
    yj_code: YjCode | None
    payload: dict[str, JsonValue]
