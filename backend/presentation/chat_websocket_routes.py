"""リアルタイムAIチャットおよび根拠引用ストリーミング用 WebSocket エンドポイント"""

from __future__ import annotations

import asyncio
import re
from contextlib import aclosing as closing_stream
from contextlib import suppress
from json import JSONDecodeError
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, ValidationError, field_validator

from backend.application.medicine.errors import InvalidMedicineInput
from backend.application.medicine.queries.catalog import (
    MedicineQueries,
)

from .chat_models import ChatMessage
from .chat_service import AppChatService as ChatService
from .dependencies import get_chat_service
from .evidence_models import ChatSource
from .medicine_models import MAX_PRODUCT_YJ_CODES

ALLOWED_PROVIDER_NAMES: set[str] = {"openai", "gemini"}


ALLOWED_MODELS_BY_PROVIDER: dict[str, set[str]] = {
    "openai": {"gpt-6-luna", "gpt-5.6-luna", "luna"},
    "gemini": {"gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.5-pro"},
}


class WebSocketChatRequest(BaseModel):
    """WebSocket 経由で受信するチャットリクエストペイロード"""

    type: Literal["message"] = "message"
    request_id: str
    product_yj_codes: list[str] = Field(min_length=1, max_length=MAX_PRODUCT_YJ_CODES)
    messages: list[ChatMessage] = Field(min_length=1, max_length=50)
    provider: str | None = Field(default=None, max_length=50)
    model: str | None = Field(default=None, max_length=100)

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


UUID4 = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)


def valid_id(value: object) -> bool:
    return isinstance(value, str) and UUID4.fullmatch(value) is not None


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

    send_lock = asyncio.Lock()
    disconnected = False
    send_failed = asyncio.Event()

    async def send_wire(event: dict[str, Any]) -> None:
        nonlocal disconnected
        async with send_lock:
            if disconnected:
                return
            try:
                await websocket.send_json(event)
            except Exception:
                disconnected = True
                send_failed.set()
                raise

    active: asyncio.Task[None] | None = None
    active_id: str | None = None
    abort_requested = False
    terminal = False

    async def generate(payload: WebSocketChatRequest, request_id: str) -> None:
        async def send(event: dict[str, Any]) -> None:
            nonlocal terminal
            if terminal:
                return
            if event["type"] in {"text_done", "error", "aborted"}:
                terminal = True
            await send_wire({**event, "request_id": request_id})

        try:
            if not service:
                try:
                    MedicineQueries.validate_product_codes(payload.product_yj_codes)
                except InvalidMedicineInput as exc:
                    await send({"type": "error", "content": str(exc)})
                    return
                await send({"type": "error", "content": "Medicine corpus is not ready"})
                return

            jev_was_searched = service.is_jev_available
            if not service.is_jev_available:
                await send({"type": "retrieval_status", "stage": "unavailable"})
            else:
                await send({"type": "retrieval_status", "stage": "jev_searching"})

            async def publish_logic(sources: list[ChatSource]) -> None:
                await send(
                    {"type": "sources", "sources": [s.model_dump() for s in sources]}
                )

            try:
                reply = await service.prepare_reply(
                    payload.messages,
                    payload.product_yj_codes,
                    on_logic_sources=publish_logic,
                )

            except InvalidMedicineInput as exc:
                await send({"type": "error", "content": str(exc)})
                return

            if not reply.needs_clarification:
                if reply.sources:
                    await send(
                        {
                            "type": "sources",
                            "sources": [
                                s.model_dump()
                                for s in service.sources_to_api(reply.sources)
                            ],
                        }
                    )
                if reply.jev_response is not None:
                    await send({"type": "jev_response", "data": reply.jev_response})
                if reply.notices:
                    await send({"type": "notices", "notices": reply.notices})
                if jev_was_searched:
                    await send(
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
                    await send({"type": "text_delta", "content": chunk})

            await send({"type": "text_done"})
        except asyncio.CancelledError:
            if abort_requested:
                await send({"type": "aborted"})
            raise
        except Exception:
            await send({"type": "error", "content": "Answer generation failed"})

    async def join_active() -> None:
        if active is not None:
            while not active.done():
                try:
                    await asyncio.shield(active)
                except asyncio.CancelledError:
                    if active.done():
                        break
            with suppress(asyncio.CancelledError):
                active.result()

    receive_task: asyncio.Task[Any] | None = None
    failed_task = asyncio.create_task(send_failed.wait())
    try:
        while True:
            try:
                receive_task = asyncio.create_task(websocket.receive_json())
                done, _ = await asyncio.wait(
                    {receive_task, failed_task}, return_when=asyncio.FIRST_COMPLETED
                )
                if failed_task in done:
                    break
                data = receive_task.result()
            except JSONDecodeError:
                await send_wire(
                    {
                        "type": "connection_error",
                        "code": "invalid_payload",
                        "content": "Invalid JSON",
                    }
                )
                continue
            if not isinstance(data, dict):
                await send_wire(
                    {
                        "type": "connection_error",
                        "code": "invalid_payload",
                        "content": "Payload must be a JSON object",
                    }
                )
                continue
            msg_type = data.get("type")
            if not isinstance(msg_type, str) or msg_type not in {
                "ping",
                "message",
                "abort",
            }:
                await send_wire(
                    {
                        "type": "connection_error",
                        "code": "unsupported_type",
                        "content": "Unsupported message type",
                    }
                )
                continue
            id_field = "ping_id" if msg_type == "ping" else "request_id"
            if not valid_id(data.get(id_field)):
                await send_wire(
                    {
                        "type": "connection_error",
                        "code": "invalid_payload",
                        "content": "Expected UUID v4",
                    }
                )
                continue
            request_id = data[id_field].lower()
            if msg_type == "ping":
                await send_wire({"type": "pong", "ping_id": request_id})
                continue
            if msg_type == "abort":
                if (
                    active is not None
                    and not active.done()
                    and request_id == active_id
                    and not terminal
                ):
                    if not abort_requested:
                        abort_requested = True
                        active.cancel()
                else:
                    await send_wire(
                        {
                            "type": "control_error",
                            "request_id": request_id,
                            "code": "not_active",
                            "content": "No active request",
                        }
                    )
                continue

            if active is not None and not active.done():
                await send_wire(
                    {
                        "type": "control_error",
                        "request_id": request_id,
                        "code": "busy",
                        "content": "A request is active",
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
                await send_wire(
                    {"type": "error", "request_id": request_id, "content": err_msg}
                )
                continue

            if active is not None:
                await join_active()
            abort_requested = False
            terminal = False
            active_id = request_id
            active = asyncio.create_task(generate(payload, request_id))

    except WebSocketDisconnect:
        disconnected = True
    except Exception:
        disconnected = True

    finally:
        disconnected = True
        for child in (receive_task, failed_task):
            if child is not None:
                child.cancel()
                with suppress(asyncio.CancelledError, WebSocketDisconnect):
                    await child
        if active is not None:
            if not active.done() and not abort_requested:
                active.cancel()
            await join_active()
