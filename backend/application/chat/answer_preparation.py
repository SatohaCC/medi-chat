"""回答準備の技術非依存入口。"""

from collections.abc import Sequence

from backend.application.medicine.product_contracts import RegisteredMedicineReader
from backend.application.retrieval.evidence_contracts import EvidenceRepository
from backend.application.retrieval.search_models import Evidence, IntentPolicy

from ..retrieval.intent_contracts import IntentClassifier
from ..retrieval.keyword_contracts import KeywordExtractor
from ..retrieval.retrieve_evidence import SourcesCallback, retrieve_evidence
from ..retrieval.snapshot_contracts import RetrievalSnapshotProvider
from .chat_models import ChatMessage, ChatResponse


async def prepare_reply(
    conversation: Sequence[ChatMessage],
    product_yj_codes: list[str],
    *,
    medicine_reader: RegisteredMedicineReader,
    evidence_reader: EvidenceRepository,
    intent_classifier: IntentClassifier,
    keyword_extractor: KeywordExtractor,
    intent_policy: IntentPolicy,
    snapshot_provider: RetrievalSnapshotProvider | None = None,
    on_logic_sources: SourcesCallback | None = None,
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
        on_logic_sources=on_logic_sources,
    )
    if result.needs_clarification:
        answer = (
            "対象医薬品を@医薬品から選択してください。"
            if not product_yj_codes
            else "指定されたYJコードのすべてに対応する電子添文が、現在の検索データにありません。"
        )
    else:
        answer = _summarize_evidence(result.sources)
    return ChatResponse(
        answer=answer,
        intent=result.intent,
        retrieval_strategy=result.retrieval_strategy,
        resolved_medicines=result.resolved_medicines,
        sources=result.sources,
        needs_clarification=result.needs_clarification,
        notices=result.notices,
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
