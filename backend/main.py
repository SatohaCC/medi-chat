"""FastAPI エントリーポイント（REST エンドポイントおよび WebSocket チャットストリーミング）"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config.database_settings import resolve_postgres_database_settings
from .config.origin_settings import read_allowed_origins
from .config.runtime_environment import load_runtime_environment
from .infrastructure.composition.app_lifespan import create_app_lifespan
from .infrastructure.intent.jev_classifier import JevIntentClassifier
from .infrastructure.morphology.janome_keyword_extractor import (
    JanomeKeywordExtractor,
)
from .infrastructure.morphology.keyword_extraction import get_janome_tokenizer
from .infrastructure.package_insert_definitions.loader import (
    get_package_insert_definitions,
)
from .presentation.chat_service import AppChatService

# ローカル環境変数の読み込み
load_runtime_environment()


__all__ = ["create_app", "app"]


def create_app(
    structured_dir: Path | None = None,
    index_path: Path | None = None,
    llm_provider_factory: Callable[[str | None], Any] | None = None,
    *,
    database_url: str | None = None,
    import_directory: Path | None = None,
    _readonly_probe: bool = False,
    _database_schema: str | None = None,
) -> FastAPI:
    """FastAPI アプリケーションインスタンスを生成・設定する"""
    definitions = get_package_insert_definitions()
    if (
        structured_dir is not None
        or index_path is not None
        or import_directory is not None
    ):
        raise ValueError("Legacy runtime file settings are not supported")
    settings = resolve_postgres_database_settings(database_url=database_url)
    lifespan = create_app_lifespan(
        definitions=definitions,
        settings=settings,
        chat_service_factory=AppChatService,
        llm_provider_factory=llm_provider_factory,
        readonly_probe=_readonly_probe,
        intent_classifier_cls=JevIntentClassifier,
        keyword_extractor_cls=JanomeKeywordExtractor,
        database_schema=_database_schema
        or os.environ.get("MEDI_CHAT_DATABASE_SCHEMA", "public"),
        janome_initializer=get_janome_tokenizer,
    )

    application = FastAPI(
        title="medi-chat API",
        description="Search PMDA package inserts and real-time streaming AI chat.",
        version="0.2.0",
        lifespan=lifespan,
    )

    # Next.js フロントエンド向けの CORS 設定
    allowed_origins = read_allowed_origins()
    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    # WebSocket での検証用に許可オリジンを app.state に保持
    application.state.allowed_origins = allowed_origins

    # 分割された API ルーターの登録
    from .presentation import (
        chat_router,
        chat_websocket_router,
        health_router,
        medicine_router,
        search_router,
    )

    application.include_router(health_router)
    application.include_router(medicine_router)
    application.include_router(search_router)
    application.include_router(chat_router)
    application.include_router(chat_websocket_router)
    from .presentation.attachment_import_routes import router as import_router

    application.include_router(import_router)

    return application


app = create_app()
