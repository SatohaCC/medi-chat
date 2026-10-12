"""システムヘルスチェックおよび診断用エンドポイント"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from .dependencies import get_document_store


class HealthResponse(BaseModel):
    """システムヘルスチェックレスポンスモデル"""

    status: str
    document_count: int
    unit_count: int
    generation_id: str


router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse, name="health")
async def get_document_store_health(
    request: Request,
    document_store: Annotated[Any, Depends(get_document_store)],
) -> HealthResponse:
    """読み込まれた医薬品コーパスの稼働状態および統計情報を確認する"""
    if document_store is None:
        raise HTTPException(status_code=503, detail="Medicine corpus is not ready")
    stats = await request.app.state.generation_runtime.statistics()
    return HealthResponse(
        status="ok",
        generation_id=str(stats["generation_id"]),
        document_count=int(stats["document_count"]),
        unit_count=int(stats["unit_count"]),
    )


@router.get("/api", name="api_health")
@router.get("/api/", name="api_health")
async def get_api_status() -> dict[str, str]:
    """軽量なヘルスチェックプローブ用エンドポイント"""
    return {"status": "ok"}
