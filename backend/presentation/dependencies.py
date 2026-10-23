"""APIルート用 FastAPI 依存関係関数"""

from __future__ import annotations

from typing import Any

from starlette.requests import HTTPConnection

from backend.application.attachment_import.commands.import_documents import (
    AttachmentImportCommands,
)
from backend.application.attachment_import.queries.import_history import (
    ImportHistoryQueries,
)
from backend.application.medicine.queries.catalog import (
    MedicineQueries,
)
from backend.application.medicine.queries.suggest_medicines import MedicineSuggester

from .chat_service import AppChatService as ChatService


def get_chat_service(connection: HTTPConnection) -> ChatService:
    """チャットサービスを取得する依存関係関数"""
    return getattr(connection.app.state, "chat_service", None)  # type: ignore[return-value, no-any-return]


def get_import_service(connection: HTTPConnection) -> AttachmentImportCommands:
    """添付文書取り込みサービスを取得する依存関係関数"""
    return connection.app.state.attachment_import_service  # type: ignore[no-any-return]


async def get_medicine_suggester(connection: HTTPConnection) -> MedicineSuggester:
    """医薬品候補提示サービスを取得する依存関係関数"""
    runtime = getattr(connection.app.state, "generation_runtime", None)
    if runtime is not None:
        return await runtime.catalogue()
    return getattr(connection.app.state, "medicine_suggester", None)  # type: ignore[return-value, no-any-return]


def get_medicine_service(connection: HTTPConnection) -> MedicineQueries:
    """医薬品カタログのApplication入口を取得する。"""
    return MedicineQueries(runtime=connection.app.state.generation_runtime)


def get_document_store(connection: HTTPConnection) -> Any:
    """ドキュメントストアを取得する依存関係関数"""
    return getattr(connection.app.state, "document_store", None)


def get_import_queries(connection: HTTPConnection) -> ImportHistoryQueries:
    return connection.app.state.attachment_import_queries  # type: ignore[no-any-return]
