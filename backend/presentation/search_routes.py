"""添付文書キーワード検索 REST API エンドポイント"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ..application.medicine.product_contracts import RegisteredMedicineReader
from ..application.retrieval.search_keywords import search_evidence_by_keywords
from ..domain.retrieval.repositories import EvidenceRepository
from .chat_dto_mapper import evidence_to_api
from .chat_service import AppChatService
from .dependencies import (
    get_chat_service,
    get_evidence_reader,
    get_medicine_reader,
)
from .search_models import KeywordSearchResponse

router = APIRouter(tags=["search"])


@router.get(
    "/api/search",
    response_model=KeywordSearchResponse,
    name="keyword_search",
)
async def search_package_inserts(
    chat_service: Annotated[AppChatService | None, Depends(get_chat_service)],
    medicine_reader: Annotated[
        RegisteredMedicineReader | None, Depends(get_medicine_reader)
    ],
    evidence_reader: Annotated[EvidenceRepository | None, Depends(get_evidence_reader)],
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
    keyword_extractor = getattr(chat_service, "keyword_extractor", None)
    snapshot_provider = getattr(chat_service, "snapshot_provider", None)

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

    items = [evidence_to_api(e) for e in results]
    return KeywordSearchResponse(query=q, items=items, total_count=len(items))
