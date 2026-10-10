"""任意のclose能力を持つ非同期streamを利用側の期間に閉じる。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Protocol, runtime_checkable


@runtime_checkable
class AsyncClosable(Protocol):
    async def aclose(self) -> None: ...


@asynccontextmanager
async def closing_stream[T](
    stream: AsyncIterator[T],
) -> AsyncIterator[AsyncIterator[T]]:
    try:
        yield stream
    finally:
        if isinstance(stream, AsyncClosable):
            await stream.aclose()
