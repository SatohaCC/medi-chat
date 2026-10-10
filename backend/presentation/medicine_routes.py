"""医薬品カタログ取得およびオートコンプリート検索エンドポイント"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from ..application.medicine.suggestions import MedicineSuggester
from .dependencies import get_medicine_suggester
from .medicine_models import MedicineMatch


class MedicineListResponse(BaseModel):
    """医薬品候補一覧レスポンスモデル"""

    items: list[MedicineMatch]


router = APIRouter(tags=["catalog"])


@router.get("/api/medicines", response_model=MedicineListResponse, name="medicines")
def list_medicines(
    suggester: Annotated[MedicineSuggester, Depends(get_medicine_suggester)],
    query: Annotated[str | None, Query(max_length=200)] = None,
) -> MedicineListResponse:
    """入力クエリに合致する医薬品、または未指定時は全医薬品カタログを返却する"""
    return MedicineListResponse(
        items=[
            MedicineMatch(
                generic_name=item.generic_name,
                brand_names=list(item.brand_names),
                yj_codes=[code.value for code in item.yj_codes],
                document_ids=[code.value for code in item.document_ids],
                matched_aliases=list(item.matched_aliases),
            )
            for item in suggester.suggest(query)
        ]
    )
