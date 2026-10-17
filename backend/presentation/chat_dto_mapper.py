"""APIの会話モデルとアプリケーションの純粋値との変換。"""

from copy import deepcopy

from backend.application.medicine.product_models import (
    MedicineMatch as DomainMedicineMatch,
)
from backend.application.medicine.product_models import (
    ResolvedMedicine,
    YjCode,
)

from ..application.chat.chat_models import ChatMessage, ChatResponse
from ..application.retrieval.retrieval_models import (
    DetectionSource,
    DocumentId,
    DocumentRevision,
    Evidence,
    EvidenceColumns,
    EvidenceReference,
    EvidenceSection,
    SearchUnitId,
)
from .chat_models import ChatMessage as ApiChatMessage
from .chat_models import ChatResponse as ApiChatResponse
from .evidence_models import ChatSource as ApiChatSource
from .medicine_models import MedicineMatch as ApiMedicineMatch


def chat_message_from_api(value: ApiChatMessage) -> ChatMessage:
    return ChatMessage(role=value.role, content=value.content)


def chat_message_to_api(value: ChatMessage) -> ApiChatMessage:
    return ApiChatMessage(role=value.role, content=value.content)


def chat_response_from_api(value: ApiChatResponse) -> ChatResponse:
    return ChatResponse(
        answer=value.answer,
        intent=value.intent,
        retrieval_strategy=value.retrieval_strategy,
        resolved_medicines=[
            _medicine_from_api(medicine) for medicine in value.resolved_medicines
        ],
        sources=[_evidence_from_api(source) for source in value.sources],
        needs_clarification=value.needs_clarification,
        notices=list(value.notices),
        jev_response=deepcopy(value.jev_response),
        qualifying_intents=_qualifying_intents_from_api(value),
    )


def chat_response_to_api(value: ChatResponse) -> ApiChatResponse:
    return ApiChatResponse.model_validate(
        {
            "answer": value.answer,
            "intent": value.intent,
            "retrieval_strategy": value.retrieval_strategy,
            "resolved_medicines": [
                medicine_match_to_api(medicine).model_dump()
                for medicine in value.resolved_medicines
            ],
            "sources": [source.to_dict() for source in value.sources],
            "needs_clarification": value.needs_clarification,
            "notices": list(value.notices),
            "jev_response": deepcopy(value.jev_response),
        }
    )


def _qualifying_intents_from_api(value: ApiChatResponse) -> tuple[str, ...]:
    qualifying = (
        value.jev_response.get("qualifying_intents") if value.jev_response else None
    )
    return (
        tuple(name for name in qualifying if isinstance(name, str))
        if isinstance(qualifying, list)
        else ()
    )


def medicine_match_to_api(value: ResolvedMedicine) -> ApiMedicineMatch:
    return ApiMedicineMatch(
        generic_name=value.generic_name,
        brand_names=list(value.brand_names),
        yj_codes=list(value.yj_codes),
        document_ids=list(value.document_ids),
        matched_aliases=list(value.matched_aliases),
    )


def _medicine_from_api(value: ApiMedicineMatch) -> ResolvedMedicine:
    return ResolvedMedicine(
        medicine=DomainMedicineMatch(
            generic_name=value.generic_name,
            brand_names=tuple(value.brand_names),
            yj_codes=tuple(value.yj_codes),
            matched_aliases=tuple(value.matched_aliases),
        ),
        document_ids=tuple(value.document_ids),
    )


def evidence_to_api(value: Evidence) -> ApiChatSource:
    return ApiChatSource.model_validate(value.to_dict())


def _evidence_from_api(value: ApiChatSource) -> Evidence:
    return Evidence(
        unit_id=SearchUnitId(value.unit_id),
        document_id=DocumentId(value.document_id),
        product_name=value.product_name,
        generic_name=value.generic_name,
        product_yj_codes=tuple(YjCode(code) for code in value.product_yj_codes),
        document_revision=DocumentRevision(value.document_revision),
        section=EvidenceSection(value.section),
        kind=value.kind,
        excerpt=value.excerpt,
        columns=EvidenceColumns(value.columns) if value.columns is not None else None,
        references=tuple(EvidenceReference(ref) for ref in value.references),
        url=value.url,
        retrieved_by=frozenset(
            DetectionSource(source) for source in value.retrieved_by
        ),
    )
