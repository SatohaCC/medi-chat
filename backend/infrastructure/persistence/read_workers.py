"""読取workerの処理上限と終了待ちを所有する外側の境界。"""

import asyncio
import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import TypeVar
from weakref import WeakKeyDictionary

from sqlalchemy.engine import Engine

T = TypeVar("T")


class ReadWorkers:
    def __init__(self, *, max_workers: int = 4) -> None:
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="index-read"
        )
        self._lock = threading.Lock()
        self._closed = False

    async def run(self, operation: Callable[[], T]) -> T:
        with self._lock:
            if self._closed:
                raise RuntimeError("Read workers are closed")
            native = self._executor.submit(operation)
        native.add_done_callback(self._completed)
        result = asyncio.wrap_future(native)
        # 呼出しのcancelでnative futureを完了/cancel扱いにしない。
        # await側が離れた後に失敗してもasync Futureの例外を回収する。
        result.add_done_callback(
            lambda future: None if future.cancelled() else future.exception()
        )
        # waitは呼出しのcancelをresultへ伝播しない。shieldはPython 3.14で
        # 離脱後の例外をloopへ報告するため、ここでは既存の回収処理で管理する。
        await asyncio.wait((result,))
        return result.result()

    @staticmethod
    def _completed(future: Future[T]) -> None:
        if not future.cancelled():
            future.exception()

    async def aclose(self) -> None:
        with self._lock:
            self._closed = True
        # shutdown(wait=True)は開始済/待機中native処理のConnection closeまで待つ。
        cleanup = asyncio.create_task(
            asyncio.to_thread(self._executor.shutdown, wait=True)
        )
        cancelled = False
        while not cleanup.done():
            try:
                await asyncio.shield(cleanup)
            except asyncio.CancelledError:
                cancelled = True
        cleanup.result()
        if cancelled:
            raise asyncio.CancelledError


# 直接readerを構築する既存CLI/テスト用。主たる所有者はcompositionが明示注入する。
# ownerはEngineを保持しないので、このfallbackがEngineの寿命を延ばさない。
_fallback_workers: WeakKeyDictionary[Engine, ReadWorkers] = WeakKeyDictionary()
_fallback_lock = threading.Lock()


def read_workers_for_engine(engine: Engine) -> ReadWorkers:
    with _fallback_lock:
        workers = _fallback_workers.get(engine)
        if workers is None:
            workers = ReadWorkers()
            _fallback_workers[engine] = workers
        return workers
