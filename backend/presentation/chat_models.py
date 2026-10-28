"""会話メッセージと回答をAPI・サービス・プロンプトで共有するモデル。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from .evidence_models import ChatSource
from .medicine_models import MedicineMatch


class ChatMessage(BaseModel):
    """チャット対話メッセージモデル"""

    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1, max_length=4000)

    @field_validator("content")
    @classmethod
    def validate_message_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content must contain non-whitespace characters")
        return value.strip()


class ChatResponse(BaseModel):
    """チャット応答および根拠ソースを含むレスポンスモデル"""

    answer: str
    feedback_token: str | None = None
    intent: str
    retrieval_strategy: str
    resolved_medicines: list[MedicineMatch] = Field(default_factory=list)
    sources: list[ChatSource] = Field(default_factory=list)
    needs_clarification: bool = False
    notices: list[str] = Field(default_factory=list)
    jev_response: dict[str, Any] | None = None
