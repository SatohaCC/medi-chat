"""システムヘルスチェックおよび診断用エンドポイント"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .dependencies import get_document_store


class HealthResponse(BaseModel):
    """システムヘルスチェックレスポンスモデル"""

    status: str
    document_count: int
    unit_count: int


router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse, name="health")
def get_document_store_health(
    document_store: Annotated[Any, Depends(get_document_store)],
) -> HealthResponse:
    """読み込まれた医薬品コーパスの稼働状態および統計情報を確認する"""
    if document_store is None:
        raise HTTPException(status_code=503, detail="Medicine corpus is not ready")
    return HealthResponse(status="ok", **document_store.index_stats)


@router.get("/api", name="api_health")
@router.get("/api/", name="api_health")
async def get_api_status() -> dict[str, str]:
    """軽量なヘルスチェックプローブ用エンドポイント"""
    return {"status": "ok"}
