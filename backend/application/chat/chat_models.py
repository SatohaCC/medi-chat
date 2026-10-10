"""会話メッセージと回答を表す純粋な値。"""

from dataclasses import dataclass, field
from typing import Literal

from ...domain.attachment.value_objects import AttachmentProductMatch
from ...domain.json_types import JsonValue
from ...domain.retrieval.value_objects import Evidence


@dataclass
class ChatMessage:
    """チャット対話メッセージ。"""

    role: Literal["user", "assistant", "system"]
    content: str


@dataclass
class ChatResponse:
    """チャット応答と根拠。"""

    answer: str
    intent: str
    retrieval_strategy: str
    resolved_medicines: list[AttachmentProductMatch] = field(default_factory=list)
    sources: list[Evidence] = field(default_factory=list)
    needs_clarification: bool = False
    notices: list[str] = field(default_factory=list)
    jev_response: dict[str, JsonValue] | None = None
    qualifying_intents: tuple[str, ...] = ()
