"""APIの会話モデルとアプリケーションの純粋値との変換。"""

from copy import deepcopy

from backend.application.chat.queries.models import ChatMessage, ChatResponse
from backend.application.medicine.queries.models import ResolvedMedicine
from backend.application.retrieval.queries.dtos.evidence import evidence_payload
from backend.application.retrieval.queries.models import Evidence

from .chat_models import ChatMessage as ApiChatMessage
from .chat_models import ChatResponse as ApiChatResponse
from .evidence_models import ChatSource as ApiChatSource
from .medicine_models import MedicineMatch as ApiMedicineMatch


def chat_message_from_api(value: ApiChatMessage) -> ChatMessage:
    return ChatMessage(role=value.role, content=value.content)


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
            "sources": [evidence_payload(source) for source in value.sources],
            "needs_clarification": value.needs_clarification,
            "notices": list(value.notices),
            "jev_response": deepcopy(value.jev_response),
        }
    )


def medicine_match_to_api(value: ResolvedMedicine) -> ApiMedicineMatch:
    return ApiMedicineMatch(
        generic_name=value.generic_name,
        brand_names=list(value.brand_names),
        yj_codes=list(value.yj_codes),
        document_ids=list(value.document_ids),
        matched_aliases=list(value.matched_aliases),
    )


def evidence_to_api(value: Evidence) -> ApiChatSource:
    return ApiChatSource.model_validate(evidence_payload(value))
