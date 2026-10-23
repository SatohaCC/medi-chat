"""医薬品カタログ取得およびオートコンプリート検索エンドポイント"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.application.medicine.queries.catalog import (
    MedicineQueries,
)
from backend.application.medicine.queries.suggest_medicines import MedicineSuggester

from .dependencies import get_medicine_service, get_medicine_suggester
from .medicine_models import MedicineMatch


class MedicineListResponse(BaseModel):
    """医薬品候補一覧レスポンスモデル"""

    items: list[MedicineMatch]
    generation_id: str


router = APIRouter(tags=["catalog"])


@router.get("/api/medicines", response_model=MedicineListResponse, name="medicines")
def list_medicines(
    suggester: Annotated[MedicineSuggester, Depends(get_medicine_suggester)],
) -> MedicineListResponse:
    """全医薬品カタログを返却する"""
    if suggester.generation_id is None:
        raise HTTPException(503, "Medicine generation is not ready")
    return MedicineListResponse(
        generation_id=suggester.generation_id.value,
        items=[
            MedicineMatch(
                generic_name=item.generic_name,
                brand_names=list(item.brand_names),
                yj_codes=[code.value for code in item.yj_codes],
                document_ids=[code.value for code in item.document_ids],
            )
            for item in suggester.list_all()
        ],
    )


class CompactMedicineResponse(BaseModel):
    n: str
    k: str
    h: str
    y: str
    g: str
    c: str


class AutocompleteResponse(BaseModel):
    generation_id: str
    items: list[CompactMedicineResponse]


@router.get("/api/medicines/autocomplete", response_model=AutocompleteResponse)
async def autocomplete(
    service: Annotated[MedicineQueries, Depends(get_medicine_service)],
) -> AutocompleteResponse:
    generation_id, items = await service.read_autocomplete_catalog()
    return AutocompleteResponse(
        generation_id=generation_id.value,
        items=[CompactMedicineResponse(**item) for item in items],
    )
