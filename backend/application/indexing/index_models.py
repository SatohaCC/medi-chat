"""技術に依存しない索引構築用の値。"""

from dataclasses import dataclass

from ...domain.foundation.json_types import JsonValue


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
