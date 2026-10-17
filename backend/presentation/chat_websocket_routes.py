"""リアルタイムAIチャットおよび根拠引用ストリーミング用 WebSocket エンドポイント"""

from __future__ import annotations

from contextlib import suppress
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, ValidationError, field_validator

from ..application.chat.stream_closing import closing_stream
from .chat_models import ChatMessage
from .chat_service import AppChatService as ChatService
from .dependencies import get_chat_service
from .evidence_models import ChatSource
from .medicine_models import YJCode

ALLOWED_PROVIDER_NAMES: set[str] = {"openai", "gemini"}


ALLOWED_MODELS_BY_PROVIDER: dict[str, set[str]] = {
    "openai": {"gpt-6-luna", "gpt-5.6-luna", "luna"},
    "gemini": {"gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.5-pro"},
}


class WebSocketChatRequest(BaseModel):
    """WebSocket 経由で受信するチャットリクエストペイロード"""

    type: Literal["message"] = "message"
    product_yj_codes: list[YJCode] = Field(min_length=1, max_length=8)
    messages: list[ChatMessage] = Field(min_length=1, max_length=50)
    provider: str | None = Field(default=None, max_length=50)
    model: str | None = Field(default=None, max_length=100)

    @field_validator("product_yj_codes")
    @classmethod
    def validate_unique_product_codes(cls, value: list[YJCode]) -> list[YJCode]:
        if len(value) != len(set(value)):
            raise ValueError("product_yj_codes must not contain duplicates")
        return value

    @field_validator("messages")
    @classmethod
    def validate_user_message_presence(
        cls, value: list[ChatMessage]
    ) -> list[ChatMessage]:
        if not any(m.role == "user" for m in value):
            raise ValueError("messages must contain at least one user message")
        return value

    @field_validator("provider")
    @classmethod
    def validate_provider_name(cls, value: str | None) -> str | None:
        if value is not None and value not in ALLOWED_PROVIDER_NAMES:
            raise ValueError(
                f"Unsupported provider '{value}'. Allowed: {sorted(ALLOWED_PROVIDER_NAMES)}"
            )
        return value

    @field_validator("model")
    @classmethod
    def validate_model_name(cls, value: str | None, info: Any) -> str | None:
        if value is None:
            return value
        provider = (info.data.get("provider") if info.data else None) or "openai"
        allowed = ALLOWED_MODELS_BY_PROVIDER.get(provider, set())
        if value not in allowed:
            raise ValueError(
                f"Unsupported model '{value}' for provider '{provider}'. Allowed: {sorted(allowed)}"
            )
        return value


router = APIRouter(tags=["chat"])


@router.websocket("/api/ws", name="websocket_chat")
@router.websocket("/ws/chat", name="websocket_chat")
async def stream_chat_response(
    websocket: WebSocket,
    service: Annotated[ChatService | None, Depends(get_chat_service)] = None,
) -> None:
    """WebSocket 経由での対話型リアルタイムストリーミングチャットセッションを処理する"""
    allowed_origins = getattr(websocket.app.state, "allowed_origins", [])
    origin = websocket.headers.get("origin")
    if origin and origin not in allowed_origins and "*" not in allowed_origins:
        await websocket.close(code=1008, reason="Origin not allowed")
        return

    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()
            if not isinstance(data, dict):
                await websocket.send_json(
                    {"type": "error", "content": "Payload must be a JSON object"}
                )
                continue

            msg_type = data.get("type", "message")
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if msg_type != "message":
                await websocket.send_json(
                    {
                        "type": "error",
                        "content": f"Unsupported message type: {msg_type}",
                    }
                )
                continue

            try:
                payload = WebSocketChatRequest.model_validate(data)
            except ValidationError as exc:
                first_error = exc.errors()[0]
                field_name = (
                    str(first_error["loc"][-1]) if first_error.get("loc") else "payload"
                )
                err_msg = f"Validation error on {field_name}: {first_error['msg']}"
                await websocket.send_json({"type": "error", "content": err_msg})
                continue

            if not service:
                await websocket.send_json(
                    {"type": "error", "content": "Medicine corpus is not ready"}
                )
                continue

            jev_was_searched = service.is_jev_available
            if not service.is_jev_available:
                await websocket.send_json(
                    {"type": "retrieval_status", "stage": "unavailable"}
                )
            else:
                await websocket.send_json(
                    {"type": "retrieval_status", "stage": "jev_searching"}
                )

            async def publish_logic(sources: list[ChatSource]) -> None:
                await websocket.send_json(
                    {"type": "sources", "sources": [s.model_dump() for s in sources]}
                )

            reply = await service.prepare_reply(
                payload.messages,
                payload.product_yj_codes,
                on_logic_sources=publish_logic,
            )

            if not reply.needs_clarification:
                if reply.sources:
                    await websocket.send_json(
                        {
                            "type": "sources",
                            "sources": [
                                s.model_dump()
                                for s in service.sources_to_api(reply.sources)
                            ],
                        }
                    )
                if reply.jev_response is not None:
                    await websocket.send_json(
                        {"type": "jev_response", "data": reply.jev_response}
                    )
                if reply.notices:
                    await websocket.send_json(
                        {"type": "notices", "notices": reply.notices}
                    )
                if jev_was_searched:
                    await websocket.send_json(
                        {
                            "type": "retrieval_status",
                            "stage": "complete",
                            "jev_response": reply.jev_response,
                        }
                    )

            async with closing_stream(
                service.stream_answer(
                    reply, payload.messages, payload.provider, payload.model
                )
            ) as response:
                async for chunk in response:
                    await websocket.send_json({"type": "text_delta", "content": chunk})

            await websocket.send_json({"type": "text_done"})

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        with suppress(Exception):
            await websocket.send_json({"type": "error", "content": str(exc)})
