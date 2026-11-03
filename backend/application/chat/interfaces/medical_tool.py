"""医療情報源・探索ツールの技術非依存な共通契約。

添付文書（電子添文）の検索や同効薬・代替薬探索、将来的には外部ガイドラインや
相互作用データベースなどの各種ツールを統一的に扱うためのインターフェースを定義します。
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from backend.application.chat.queries.models import ChatMessage
from backend.application.medicine.queries.models import ResolvedMedicine
from backend.application.retrieval.queries.models import Evidence
from backend.domain.foundation.json_types import JsonValue


@dataclass(frozen=True)
class ToolExecutionInput:
    """Tool実行時の入力パラメータを保持するコンテキストモデル。

    Attributes:
        message: ユーザーからの問い合わせ本文（検索クエリ）。
        product_yj_codes: 検索対象として指定された医薬品の個別医薬品コード（YJコード）。
        conversation: これまでの会話履歴（直近の文脈を参照する場合に使用）。
        on_sources: 検索根拠（Evidence）が見つかった際に即座に先行配信するための非同期コールバック。
    """

    message: str
    product_yj_codes: Sequence[str] = ()
    conversation: Sequence[ChatMessage] = ()
    on_sources: Callable[[list[Evidence]], Awaitable[None]] | None = None


@dataclass(frozen=True)
class ToolExecutionResult:
    """Toolの実行結果を保持するモデル。

    LLMが回答を組み立てるための根拠データ（Evidence）や、ユーザー向けの注意事項、
    特定された医薬品情報などを統合して返却します。

    Attributes:
        tool_name: 実行したツールの識別名（例: 'package_insert', 'guideline_search'）。
        sources: ツールが抽出した医療根拠（Evidence）のコレクション。
        intent: 検出または適用された意図カテゴリ（例: 'contraindication', 'alternative_suggestion'）。
        resolved_medicines: ツール内で特定・解決された医薬品の一覧。
        needs_clarification: 情報不足によりユーザーへの追加確認が必要かどうかのフラグ。
        notices: ユーザーや医療従事者に表示すべき注意喚起・免責事項のメッセージ群。
        jev_response: 意図判定の監査情報。
        qualifying_intents: 回答へ反映する複合意図。
    """

    tool_name: str
    sources: Sequence[Evidence] = ()
    intent: str = "general"
    resolved_medicines: Sequence[ResolvedMedicine] = ()
    needs_clarification: bool = False
    notices: Sequence[str] = ()
    jev_response: dict[str, JsonValue] | None = None
    qualifying_intents: tuple[str, ...] = ()


@runtime_checkable
class MedicalTool(Protocol):
    """医療情報取得・探索を行うToolの共通プロトコル（ポート）。

    各ツール（添付文書検索、同効薬探索など）はこのプロトコルに準拠して実装されます。
    特定のオーケストレーションフレームワーク（LangGraph等）に依存せず、
    独立した純粋なアプリケーションサービスとして機能します。
    """

    name: str
    description: str
    is_mandatory: bool = False

    async def execute(self, input_data: ToolExecutionInput) -> ToolExecutionResult:
        """指定された入力条件に基づいてツールを実行し、結果を返却します。"""
        raise NotImplementedError


class MedicalToolProvider(Protocol):
    """Supply request-scoped mandatory tools and release their resources afterwards."""

    def acquire(
        self, input_data: ToolExecutionInput
    ) -> AbstractAsyncContextManager[Sequence[MedicalTool]]: ...
