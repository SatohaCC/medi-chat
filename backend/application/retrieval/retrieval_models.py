"""根拠取得ユースケースの出力。"""

from dataclasses import dataclass, field

from ...domain.attachment.value_objects import AttachmentProductMatch
from ...domain.json_types import JsonValue
from ...domain.retrieval.product_identity import ProductIdentityReason
from ...domain.retrieval.value_objects import Evidence


@dataclass
class RetrievalResult:
    """チャットやLLMに依存しない検索結果。"""

    intent: str
    retrieval_strategy: str
    resolved_medicines: list[AttachmentProductMatch] = field(default_factory=list)
    sources: list[Evidence] = field(default_factory=list)
    needs_clarification: bool = False
    notices: list[str] = field(default_factory=list)
    jev_response: dict[str, JsonValue] | None = None
    qualifying_intents: tuple[str, ...] = ()
    product_identity_reason: ProductIdentityReason | None = None
