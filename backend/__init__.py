"""FastAPI backend for searching structured medicine documents."""

import asyncio
import inspect

# Python 3.14 deprecates asyncio.iscoroutinefunction in favor of inspect.iscoroutinefunction.
# Upstream libraries (e.g. langsmith) still reference asyncio.iscoroutinefunction.
if (
    hasattr(asyncio, "iscoroutinefunction")
    and asyncio.iscoroutinefunction is not inspect.iscoroutinefunction
):
    asyncio.iscoroutinefunction = inspect.iscoroutinefunction  # type: ignore[assignment]
