"""純粋な構造化JSONから索引値と検索用文字列を組み立てる。"""

from backend.application.medicine.product_models import RegisteredMedicine
from backend.domain.attachment.value_objects import MedicineDocumentReference
from backend.domain.medicine.entities import MedicineProduct

from ..application.indexing.index_models import IndexDocument, IndexUnit
from ..domain.attachment.identifiers import DocumentId
from ..domain.attachment.primitives import PmdaUrl
from ..domain.attachment.value_objects import AttachmentProductRevision
from ..domain.json_types import JsonValue
from ..domain.medicine.identifiers import YjCode
from ..domain.shared.services import normalize_search_text


def _object(value: JsonValue) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise TypeError("Expected a JSON object")
    return value


def _string(value: JsonValue) -> str:
    if not isinstance(value, str):
        raise TypeError("Expected a JSON string")
    return value


def _objects(value: JsonValue) -> list[dict[str, JsonValue]]:
    if not isinstance(value, list):
        raise TypeError("Expected a JSON array")
    return [_object(item) for item in value]


def _strings(value: JsonValue) -> list[str]:
    if not isinstance(value, list):
        raise TypeError("Expected a JSON array")
    return [_string(item) for item in value]


def build_index_unit(payload: dict[str, JsonValue], document_id: str) -> IndexUnit:
    columns = _object(payload.get("columns") or {})
    section = _object(payload.get("section") or {})
    searchable = [
        _string(payload.get("text", "")),
        " ".join(_strings(payload.get("context_labels") or [])),
        _string(section.get("title", "")),
        " ".join(str(value) for value in columns.values()),
    ]
    return IndexUnit(
        unit_id=_string(payload["unit_id"]),
        document_id=document_id,
        section_code=str(section.get("code", "")),
        kind=str(payload.get("kind", "")),
        payload=payload,
        query_text=normalize_search_text(" ".join(searchable)),
        drug_name=normalize_search_text(str(columns.get("drug_name", ""))),
    )


def build_index_document(
    payload: dict[str, JsonValue],
) -> tuple[IndexDocument, list[RegisteredMedicine]]:
    metadata = _object(payload.get("document") or {})
    source = _object(payload.get("source") or {})
    company = metadata.get("company_identifier")
    insert_no = metadata.get("package_insert_no")
    if not company or not insert_no:
        raise ValueError("Missing package insert number in document JSON")
    document_id = f"{company}_{insert_no}"
    medicines: list[RegisteredMedicine] = []
    revisions = _objects(metadata.get("revisions") or [])
    revision = revisions[-1] if revisions else {}
    for product in _objects(metadata.get("products") or []):
        yj_code = product.get("yj_code")
        medicines.append(
            RegisteredMedicine(
                medicine=MedicineProduct(
                    yj_code=YjCode(_string(yj_code)) if yj_code is not None else None,
                    brand_name=_string(product.get("brand_name") or ""),
                    generic_name=_string(metadata.get("generic_name") or ""),
                    english_name=_string(product.get("english_name") or ""),
                    hiragana_name=_string(product.get("hiragana_name") or ""),
                ),
                reference=MedicineDocumentReference(
                    document_id=DocumentId(document_id),
                    pmda_url=PmdaUrl(
                        _string(
                            source.get("pmda_url") or metadata.get("pmda_url") or ""
                        )
                    ),
                    revision=AttachmentProductRevision(revision),
                ),
            )
        )
    return IndexDocument(document_id, payload), medicines
