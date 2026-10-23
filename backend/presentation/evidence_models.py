"""検索で取得した添付文書の根拠と取得元を表す共有モデル。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from backend.application.retrieval.queries.dtos.evidence import DetectionSource


class ChatSource(BaseModel):
    """回答の根拠となった添付文書の文書単位（ソース）モデル"""

    unit_id: str
    document_id: str
    product_name: str
    generic_name: str
    product_yj_codes: list[str]
    document_revision: dict[str, Any]
    section: dict[str, str]
    kind: str
    excerpt: str
    columns: dict[str, str] | None = None
    references: list[dict[str, Any]] = Field(default_factory=list)
    url: str
    retrieved_by: list[DetectionSource] = Field(default_factory=list)
