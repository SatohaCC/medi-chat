"""会話と根拠取得をオーケストレーションするエージェントポート。

ユーザーの質問と会話履歴をもとに、登録された複数のMedicalTool（添付文書検索、代替薬探索等）を
自律的に実行・統合するエージェント機能の抽象契約を定義します。
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import Protocol, runtime_checkable

from backend.application.chat.queries.models import ChatMessage, ChatResponse
from backend.application.retrieval.queries.models import Evidence
from backend.domain.foundation.json_types import JsonValue

RetrievalCompletionCallback = Callable[[dict[str, JsonValue] | None], Awaitable[None]]


@runtime_checkable
class AgentOrchestrator(Protocol):
    """LangGraph等のエージェントエンジンが実装する技術非依存ポート。

    アプリケーション層はこのポート経由でエージェントを実行し、インフラ層に配置された
    LangGraphや外部LLMオーケストレーターへの直接依存を排除します。
    """

    async def run(
        self,
        conversation: Sequence[ChatMessage],
        product_yj_codes: Sequence[str] = (),
        *,
        provider_name: str | None = None,
        model_name: str | None = None,
        on_sources: Callable[[list[Evidence]], Awaitable[None]] | None = None,
        on_retrieval_complete: RetrievalCompletionCallback | None = None,
    ) -> ChatResponse:
        """エージェントを実行してツールを自律的に呼び出し、統合された回答と根拠を生成します。

        Args:
            conversation: 会話履歴（最新のユーザー発言を含む）。
            product_yj_codes: クライアントで指定された対象医薬品のYJコード群。
            provider_name: このリクエストで使用する生成プロバイダー。
            model_name: このリクエストで使用するモデル。
            on_sources: 根拠取得時に即座にクライアントへ先行配信するコールバック。
            on_retrieval_complete: 回答前の必須根拠取得ツールがすべて
                完了した時に呼ぶコールバック。

        Returns:
            回答本文、根拠、特定薬剤、注意事項などを格納したChatResponse。
        """
        raise NotImplementedError
