"""添付文書キーワード検索 REST API エンドポイント"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from ..application.medicine.input_values import InvalidMedicineInput, parse_yj_codes
from .chat_service import AppChatService
from .dependencies import get_chat_service
from .search_models import KeywordSearchResponse

router = APIRouter(tags=["search"])


@router.get(
    "/api/search",
    response_model=KeywordSearchResponse,
    name="keyword_search",
)
async def search_package_inserts(
    chat_service: Annotated[AppChatService | None, Depends(get_chat_service)],
    q: Annotated[
        str,
        Query(
            min_length=1,
            max_length=200,
            description="検索キーワード（スペース区切りで複数指定可）",
        ),
    ],
    yj_codes: Annotated[
        list[str] | None,
        Query(
            description="絞り込み対象の医薬品YJコード（未指定時は全医薬品を検索）",
        ),
    ] = None,
) -> KeywordSearchResponse:
    """添付文書からキーワードに合致する根拠単位を検索する"""
    try:
        if chat_service is None:
            parse_yj_codes(yj_codes or ())
            return KeywordSearchResponse(query=q, items=[], total_count=0)
        items = await chat_service.search_keywords(q, yj_codes or ())
    except InvalidMedicineInput as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return KeywordSearchResponse(query=q, items=items, total_count=len(items))
