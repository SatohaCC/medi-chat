"""APIルート用 FastAPI 依存関係関数"""

from __future__ import annotations

from typing import Any

from starlette.requests import HTTPConnection

from ..application.medicine.suggestions import MedicineSuggester
from .chat_service import AppChatService as ChatService


def get_chat_service(connection: HTTPConnection) -> ChatService:
    """チャットサービスを取得する依存関係関数"""
    return getattr(connection.app.state, "chat_service", None)  # type: ignore[no-any-return]


def get_medicine_suggester(connection: HTTPConnection) -> MedicineSuggester:
    """医薬品候補提示サービスを取得する依存関係関数"""
    return getattr(connection.app.state, "medicine_suggester", None)  # type: ignore[no-any-return]


def get_document_store(connection: HTTPConnection) -> Any:
    """ドキュメントストアを取得する依存関係関数"""
    return getattr(connection.app.state, "document_store", None)
