"""添付文書キーワード検索の入出力モデル。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .evidence_models import ChatSource


class KeywordSearchResponse(BaseModel):
    """添付文書キーワード検索のレスポンスモデル"""

    query: str
    items: list[ChatSource] = Field(default_factory=list)
    total_count: int = 0
