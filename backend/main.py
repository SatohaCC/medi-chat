"""FastAPI エントリーポイント（REST エンドポイントおよび WebSocket チャットストリーミング）"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from package_inserts.catalog_loader import get_package_insert_catalog

from .application.indexing.medicine_catalog import get_weighted_aliases
from .application.medicine.suggestions import MedicineSuggester, SuggestionProduct
from .config.database_settings import resolve_database_settings
from .config.generation_settings import read_generation_defaults
from .infrastructure.composition.index_verifier import verify_index_readiness
from .infrastructure.intent.jev_classifier import JevIntentClassifier
from .infrastructure.llm.provider_factory import create_llm_provider
from .infrastructure.morphology.janome_keyword_extractor import (
    JanomeKeywordExtractor,
)
from .infrastructure.persistence.evidence_reader import SqlAlchemyEvidenceReader
from .infrastructure.persistence.index_reader import SqlAlchemyIndexReader
from .infrastructure.persistence.medicine_reader import SqlAlchemyMedicineReader
from .infrastructure.persistence.read_workers import ReadWorkers
from .infrastructure.persistence.readonly_engine import create_readonly_engine
from .presentation.chat_service import AppChatService
from .project_paths import BACKEND_DIR, PROJECT_ROOT

# ローカル環境変数の読み込み
load_dotenv(BACKEND_DIR / ".env.local", override=True)
load_dotenv(PROJECT_ROOT / ".env.local", override=True)
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(PROJECT_ROOT / ".env")

# GEMINI_API_KEY が明示的に設定されている場合、システム環境変数の GOOGLE_API_KEY との競合を解消
if os.environ.get("GEMINI_API_KEY") and "GOOGLE_API_KEY" in os.environ:
    del os.environ["GOOGLE_API_KEY"]


__all__ = ["create_app", "app"]


def create_app(
    structured_dir: Path | None = None,
    index_path: Path | None = None,
    llm_provider_factory: Callable[[str | None], Any] | None = None,
    *,
    database_url: str | None = None,
) -> FastAPI:
    """FastAPI アプリケーションインスタンスを生成・設定する"""
    get_package_insert_catalog()
    settings = resolve_database_settings(
        structured_dir=structured_dir,
        index_path=index_path,
        database_url=database_url,
    )

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        verify_index_readiness(settings.structured_dir, settings.index_path)
        engine = create_readonly_engine(settings.index_path)
        workers = ReadWorkers(max_workers=4)
        application.state.index_engine = engine
        application.state.read_workers = workers

        index_reader = SqlAlchemyIndexReader(engine, workers=workers)
        medicine_reader = SqlAlchemyMedicineReader(engine, workers=workers)
        evidence_reader = SqlAlchemyEvidenceReader(engine, workers=workers)
        application.state.index_reader = index_reader
        application.state.medicine_reader = medicine_reader
        application.state.evidence_reader = evidence_reader

        medicines = await medicine_reader.read_medicines()
        application.state.medicine_suggester = MedicineSuggester(
            tuple(
                SuggestionProduct(
                    group_name=product.ingredient_id.value,
                    generic_name=product.generic_name,
                    brand_name=product.brand_name,
                    yj_code=product.yj_code,
                    document_id=product.document_id,
                    aliases=tuple(get_weighted_aliases(product)),
                )
                for product in medicines
            )
        )

        stats = await index_reader.read_index_stats()
        application.state.document_store = SimpleNamespace(
            index_stats=stats,
            get_document=index_reader.get_document,
            medicines=medicines,
        )

        catalog = get_package_insert_catalog()
        intent_classifier = JevIntentClassifier(catalog=catalog)
        keyword_extractor = JanomeKeywordExtractor(catalog=catalog)
        application.state.chat_service = AppChatService(
            medicine_reader=medicine_reader,
            evidence_reader=evidence_reader,
            intent_classifier=intent_classifier,
            keyword_extractor=keyword_extractor,
            catalog=catalog,
            provider_factory=llm_provider_factory or create_llm_provider,
            defaults=read_generation_defaults,
        )
        try:
            yield
        finally:
            try:
                await intent_classifier.aclose()
            finally:
                try:
                    await workers.aclose()
                finally:
                    await asyncio.to_thread(engine.dispose)

    application = FastAPI(
        title="medi-chat API",
        description="Search PMDA package inserts and real-time streaming AI chat.",
        version="0.2.0",
        lifespan=lifespan,
    )

    # Next.js フロントエンド向けの CORS 設定
    allowed_origins = [
        origin.strip()
        for origin in os.environ.get(
            "ALLOWED_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001",
        ).split(",")
        if origin.strip()
    ]
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
    )

    application.include_router(health_router)
    application.include_router(medicine_router)
    application.include_router(chat_router)
    application.include_router(chat_websocket_router)

    return application


app = create_app()
