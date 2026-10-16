"""技術に依存しない索引構築用の値。"""

from dataclasses import dataclass

from backend.application.medicine.product_models import RegisteredMedicine

from ...domain.json_types import JsonValue


@dataclass(frozen=True)
class IndexDocument:
    document_id: str
    payload: dict[str, JsonValue]


@dataclass(frozen=True)
class IndexUnit:
    unit_id: str
    document_id: str
    section_code: str
    kind: str
    payload: dict[str, JsonValue]
    query_text: str
    drug_name: str


@dataclass(frozen=True)
class SourceSnapshot:
    documents: tuple[IndexDocument, ...]
    medicines: tuple[RegisteredMedicine, ...]
    units: tuple[IndexUnit, ...]
    fingerprint: str


@dataclass(frozen=True)
class IndexBuildResult:
    document_count: int
    unit_count: int
