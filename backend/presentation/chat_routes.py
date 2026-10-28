"""医薬品添付文書の根拠引用に基づくチャット REST API エンドポイント"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from backend.application.chat.commands.submit_feedback import SubmitFeedback
from backend.application.chat.errors import (
    FeedbackForbidden,
    FeedbackTimeout,
    FeedbackUnavailable,
)
from backend.application.medicine.errors import InvalidMedicineInput

from .chat_models import ChatMessage, ChatResponse
from .chat_service import AppChatService as ChatService
from .dependencies import get_chat_service, get_feedback_command, get_feedback_user_id
from .feedback_models import FeedbackRequest, FeedbackResponse
from .medicine_models import MAX_PRODUCT_YJ_CODES


class ChatRequest(BaseModel):
    """REST API 経由で受信するチャット同期リクエストモデル"""

    message: str = Field(min_length=1, max_length=2000)
    product_yj_codes: list[str] = Field(min_length=1, max_length=MAX_PRODUCT_YJ_CODES)
    provider: str | None = None
    model: str | None = None

    @field_validator("message")
    @classmethod
    def validate_question_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must contain non-whitespace characters")
        return value.strip()


router = APIRouter(tags=["chat"])


@router.post("/api/chat", response_model=ChatResponse, name="chat")
async def create_chat_response(
    payload: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
    user_id: Annotated[str, Depends(get_feedback_user_id)],
) -> ChatResponse:
    """添付文書の根拠引用および任意のLLM文章生成を伴う質問回答を行う"""
    try:
        return await service.answer_question(
            [ChatMessage(role="user", content=payload.message)],
            payload.product_yj_codes,
            payload.provider,
            payload.model,
            user_id=user_id,
        )
    except InvalidMedicineInput as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@router.put("/api/chat/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    payload: FeedbackRequest,
    command: Annotated[SubmitFeedback | None, Depends(get_feedback_command)],
    user_id: Annotated[str, Depends(get_feedback_user_id)],
) -> FeedbackResponse:
    if not user_id:
        raise HTTPException(status_code=401, detail={"code": "authentication_required"})
    if command is None:
        raise HTTPException(status_code=503, detail={"code": "feedback_unavailable"})
    try:
        await command.execute(payload.feedback_token, user_id, payload.rating)
    except FeedbackForbidden:
        raise HTTPException(
            status_code=403, detail={"code": "feedback_forbidden"}
        ) from None
    except FeedbackTimeout:
        raise HTTPException(
            status_code=504, detail={"code": "feedback_timeout"}
        ) from None
    except FeedbackUnavailable:
        raise HTTPException(
            status_code=503, detail={"code": "feedback_unavailable"}
        ) from None
    return FeedbackResponse(rating=payload.rating)
