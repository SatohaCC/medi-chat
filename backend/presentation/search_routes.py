"""添付文書キーワード検索 REST API エンドポイント"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Request

from ..application.retrieval.search_keywords import search_evidence_by_keywords
from .evidence_models import ChatSource
from .search_models import KeywordSearchResponse

router = APIRouter(tags=["search"])


@router.get(
    "/api/search",
    response_model=KeywordSearchResponse,
    name="keyword_search",
)
async def search_package_inserts(
    request: Request,
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
    chat_service = getattr(request.app.state, "chat_service", None)
    keyword_extractor = getattr(chat_service, "keyword_extractor", None)
    snapshot_provider = getattr(chat_service, "snapshot_provider", None)

    medicine_reader = getattr(request.app.state, "medicine_reader", None)
    evidence_reader = getattr(request.app.state, "evidence_reader", None)

    if medicine_reader is None or evidence_reader is None:
        return KeywordSearchResponse(query=q, items=[], total_count=0)

    results = await search_evidence_by_keywords(
        q,
        yj_codes or (),
        medicine_reader=medicine_reader,
        evidence_reader=evidence_reader,
        keyword_extractor=keyword_extractor,
        snapshot_provider=snapshot_provider,
    )

    items = [ChatSource.model_validate(e.to_dict()) for e in results]
    return KeywordSearchResponse(query=q, items=items, total_count=len(items))
