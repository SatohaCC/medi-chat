"""FastAPI lifespanによるEngineと読取workerの所有。"""

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.engine import Engine

from ..persistence.read_workers import ReadWorkers


def create_persistence_lifespan(
    engine: Engine, *, max_workers: int = 4
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        workers = ReadWorkers(max_workers=max_workers)
        application.state.read_workers = workers
        application.state.index_engine = engine
        try:
            yield
        finally:
            try:
                await workers.aclose()
            finally:
                await asyncio.to_thread(engine.dispose)

    return lifespan
