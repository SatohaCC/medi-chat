"""検索結果を公開用の独立したpayloadへ投影する。"""

from backend.application.retrieval.queries.models import Evidence
from backend.application.retrieval.values import DetectionSource
from backend.domain.foundation.json_types import JsonValue


def evidence_payload(value: Evidence) -> dict[str, JsonValue]:
    """公開境界へ渡す、内部値から独立したJSON情報。"""
    return {
        "unit_id": value.unit_id.value,
        "document_id": value.document_id.value,
        "product_name": value.product_name.value
        if value.product_name is not None
        else "",
        "generic_name": value.generic_name.value
        if value.generic_name is not None
        else "",
        "product_yj_codes": [code.value for code in value.product_yj_codes],
        "document_revision": dict(value.document_revision),
        "section": dict(value.section),
        "kind": value.kind.value if value.kind is not None else "",
        "excerpt": value.excerpt.value,
        "columns": dict(value.columns) if value.columns is not None else None,
        "references": [dict(ref) for ref in value.references],
        "url": value.url.value if value.url is not None else "",
        "retrieved_by": [
            source.value for source in DetectionSource if source in value.retrieved_by
        ],
    }


# 根拠DTOの公開スキーマは、取得理由の列挙型も契約に含む。
__all__ = ["DetectionSource", "evidence_payload"]
