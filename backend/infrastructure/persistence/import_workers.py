"""取り込み要求全体を所有し、キャンセル回収後まで終了を待つ実行基盤。"""

import asyncio
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from typing import TypeVar

from backend.application.attachment_import.errors import ImportCancelled

T = TypeVar("T")


class ImportWorkers:
    def __init__(self, *, max_workers: int = 2) -> None:
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="attachment-import"
        )
        self._closed = False
        self._active = 0
        self._idle = asyncio.Event()
        self._idle.set()
        self._closing: asyncio.Task[None] | None = None

    async def run(
        self,
        operation: Callable[[Callable[[], None]], T],
        *,
        on_cancel: Callable[[T], None] | None = None,
    ) -> T:
        if self._closed:
            raise RuntimeError("Import service is closed")
        cancelled = threading.Event()

        def check_cancel() -> None:
            if cancelled.is_set():
                raise ImportCancelled

        # No await between admission and submission: close cannot interleave.
        self._active += 1
        self._idle.clear()
        try:
            result = asyncio.wrap_future(self._executor.submit(operation, check_cancel))
            cancellation_seen = False
            while not result.done():
                try:
                    await asyncio.shield(result)
                except asyncio.CancelledError:
                    cancellation_seen = True
                    cancelled.set()
                except Exception:
                    if not cancellation_seen:
                        raise
                    break
            if cancellation_seen:
                try:
                    value = result.result()
                except Exception:
                    pass
                else:
                    if on_cancel is not None:
                        cleanup = asyncio.wrap_future(
                            self._executor.submit(on_cancel, value)
                        )
                        while not cleanup.done():
                            with suppress(asyncio.CancelledError):
                                await asyncio.shield(cleanup)
                        cleanup.result()
                raise asyncio.CancelledError
            return result.result()
        finally:
            self._active -= 1
            if not self._active:
                self._idle.set()

    async def _shutdown(self) -> None:
        await self._idle.wait()
        await asyncio.to_thread(self._executor.shutdown, wait=True)

    async def aclose(self) -> None:
        self._closed = True
        if self._closing is None:
            self._closing = asyncio.create_task(self._shutdown())
        cancelled = False
        while not self._closing.done():
            try:
                await asyncio.shield(self._closing)
            except asyncio.CancelledError:
                cancelled = True
        self._closing.result()
        if cancelled:
            raise asyncio.CancelledError
