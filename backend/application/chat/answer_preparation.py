"""回答準備の技術非依存入口。"""

from collections.abc import Sequence

from ...domain.attachment.repositories import AttachmentProductRepository
from ...domain.retrieval.product_identity import ProductIdentityReason
from ...domain.retrieval.repositories import EvidenceRepository
from ...domain.retrieval.value_objects import Evidence, IntentPolicy
from ..retrieval.intent_contracts import IntentClassifier
from ..retrieval.keyword_contracts import KeywordExtractor
from ..retrieval.retrieve_evidence import retrieve_evidence
from ..retrieval.snapshot_contracts import RetrievalSnapshotProvider
from .chat_models import ChatMessage, ChatResponse

_PRODUCT_CONFIRMATIONS = {
    ProductIdentityReason.CONFLICT: (
        "質問の医薬品名と選択されたYJコードが一致していません。対象製品を確認し、YJコードを選択し直してください。",
        "質問の名称をもとに、選択されたYJコードを変更していません。",
    ),
    ProductIdentityReason.PAIR_REQUIRED: (
        "飲み合わせを確認する両方の医薬品のYJコードを選択してください。",
        "比較相手のYJコードを名称から自動補完していません。",
    ),
    ProductIdentityReason.UNRESOLVED: (
        "比較相手の医薬品を同定できません。相手の名称とYJコードを確認してください。",
        "比較相手を同定するまで、併用可否は回答できません。",
    ),
}


async def prepare_reply(
    conversation: Sequence[ChatMessage],
    product_yj_codes: list[str],
    *,
    medicine_reader: AttachmentProductRepository,
    evidence_reader: EvidenceRepository,
    intent_classifier: IntentClassifier,
    keyword_extractor: KeywordExtractor,
    intent_policy: IntentPolicy,
    snapshot_provider: RetrievalSnapshotProvider | None = None,
) -> ChatResponse:
    message = next(
        (item.content for item in reversed(conversation) if item.role == "user"), ""
    )
    result = await retrieve_evidence(
        message,
        product_yj_codes,
        medicine_reader=medicine_reader,
        evidence_reader=evidence_reader,
        intent_classifier=intent_classifier,
        keyword_extractor=keyword_extractor,
        intent_policy=intent_policy,
        snapshot_provider=snapshot_provider,
    )
    confirmation = (
        _PRODUCT_CONFIRMATIONS[result.product_identity_reason]
        if result.product_identity_reason is not None
        else None
    )
    if confirmation is not None:
        answer = confirmation[0]
    elif result.needs_clarification:
        answer = "指定されたYJコードのすべてに対応する電子添文が、現在の検索データにありません。"
    else:
        answer = _summarize_evidence(result.sources)
    return ChatResponse(
        answer=answer,
        intent=result.intent,
        retrieval_strategy=result.retrieval_strategy,
        resolved_medicines=result.resolved_medicines,
        sources=result.sources,
        needs_clarification=result.needs_clarification,
        notices=[confirmation[1]] if confirmation is not None else result.notices,
        jev_response=result.jev_response,
        qualifying_intents=result.qualifying_intents,
    )


def _summarize_evidence(sources: list[Evidence]) -> str:
    if not sources:
        return "検索条件に合う添付文書の記載を見つけられませんでした。"
    sections = list(
        dict.fromkeys(
            f"{source.section.get('code')} {source.section.get('title')}".strip()
            for source in sources
        )
    )
    return (
        f"関連する添付文書の記載を{len(sources)}件取得しました。"
        f"対象項目: {', '.join(sections)}。"
    )
