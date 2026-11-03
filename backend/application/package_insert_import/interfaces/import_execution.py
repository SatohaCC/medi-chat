"""取り込み要求全体の実行と、キャンセル後の結果回収を要求するポート。"""

from collections.abc import Callable
from typing import Protocol, TypeVar

T = TypeVar("T")


class ImportExecutor(Protocol):
    async def run(
        self,
        operation: Callable[[Callable[[], None]], T],
        *,
        on_cancel: Callable[[T], None] | None = None,
    ) -> T:
        """operationへ取消確認を渡す。取消時も実行完了とon_cancelの回収を待つ。"""
        ...

    async def aclose(self) -> None:
        """新規受付を停止し、受付済み要求と取消後の回収をすべて待つ。"""
        ...
