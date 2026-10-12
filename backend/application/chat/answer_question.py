"""回答準備と回答生成をつなぐ技術非依存入口。"""

from collections.abc import Callable, Sequence

from package_inserts.catalog_models import PackageInsertCatalog

from ...domain.attachment.repositories import AttachmentProductRepository
from ...domain.retrieval.repositories import EvidenceRepository
from ..retrieval.intent_contracts import IntentClassifier
from ..retrieval.keyword_contracts import KeywordExtractor
from ..retrieval.snapshot_contracts import RetrievalSnapshotProvider
from .answer_preparation import prepare_reply
from .answer_prompt_builder import build_answer_messages
from .answer_stream import stream_answer
from .chat_models import ChatMessage, ChatResponse
from .llm_contracts import LLMProvider


async def answer_question(
    conversation: Sequence[ChatMessage],
    product_yj_codes: list[str],
    *,
    medicine_reader: AttachmentProductRepository,
    evidence_reader: EvidenceRepository,
    intent_classifier: IntentClassifier,
    keyword_extractor: KeywordExtractor,
    catalog: PackageInsertCatalog,
    provider_factory: Callable[[str | None], LLMProvider],
    provider_name: str | None,
    model_name: str | None,
    snapshot_provider: RetrievalSnapshotProvider | None = None,
) -> ChatResponse:
    reply = await prepare_reply(
        conversation,
        product_yj_codes,
        medicine_reader=medicine_reader,
        evidence_reader=evidence_reader,
        intent_classifier=intent_classifier,
        keyword_extractor=keyword_extractor,
        catalog=catalog,
        snapshot_provider=snapshot_provider,
    )
    if reply.needs_clarification:
        return reply

    provider = provider_factory(provider_name)
    messages = build_answer_messages(reply, conversation, catalog=catalog)
    reply.answer = "".join(
        [chunk async for chunk in stream_answer(provider, messages, model=model_name)]
    )
    return reply
