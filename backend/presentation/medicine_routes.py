"""医薬品カタログ取得およびオートコンプリート検索エンドポイント"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from ..application.medicine.autocomplete import project_registered_product
from ..application.medicine.suggestions import MedicineSuggester
from .dependencies import get_medicine_suggester
from .medicine_models import MedicineMatch


class MedicineListResponse(BaseModel):
    """医薬品候補一覧レスポンスモデル"""

    items: list[MedicineMatch]
    generation_id: str


router = APIRouter(tags=["catalog"])


@router.get("/api/medicines", response_model=MedicineListResponse, name="medicines")
def list_medicines(
    suggester: Annotated[MedicineSuggester, Depends(get_medicine_suggester)],
    query: Annotated[str | None, Query(max_length=200)] = None,
) -> MedicineListResponse:
    """入力クエリに合致する医薬品、または未指定時は全医薬品カタログを返却する"""
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
                matched_aliases=list(item.matched_aliases),
            )
            for item in suggester.suggest(query)
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
async def autocomplete(request: Request) -> AutocompleteResponse:
    runtime = request.app.state.generation_runtime
    async with runtime.acquire() as snapshot:
        products = await snapshot.medicine_reader.read_medicines()
        return AutocompleteResponse(
            generation_id=snapshot.generation_id.value,
            items=[
                CompactMedicineResponse(**project_registered_product(product))
                for product in sorted(
                    products,
                    key=lambda product: (
                        product.yj_code.value if product.yj_code else ""
                    ),
                )
                if product.yj_code
            ],
        )
