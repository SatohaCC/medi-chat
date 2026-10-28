"""Acknowledged LangSmith feedback upsert on a bounded worker pool."""

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from functools import partial
from uuid import NAMESPACE_URL, uuid5

from langsmith import Client
from langsmith.utils import (
    LangSmithConflictError,
    LangSmithNotFoundError,
    LangSmithRequestTimeout,
)

from backend.application.chat.errors import FeedbackTimeout, FeedbackUnavailable
from backend.application.chat.values import FeedbackTarget, Rating


class LangSmithFeedback:
    def __init__(self, client: Client) -> None:
        self._client = client
        self._workers = ThreadPoolExecutor(max_workers=4, thread_name_prefix="feedback")

    def _save(self, target: FeedbackTarget, rating: Rating) -> None:
        feedback_id = uuid5(
            NAMESPACE_URL,
            json.dumps(
                [
                    "medi-chat/user_feedback/v1",
                    target.project_name,
                    str(target.run_id),
                    target.user_id,
                ],
                separators=(",", ":"),
            ),
        )
        if rating is None:
            with suppress(LangSmithNotFoundError):
                self._client.delete_feedback(feedback_id)
            return
        score = 1 if rating == "up" else 0
        try:
            self._client.update_feedback(feedback_id, score=score)
            return
        except LangSmithNotFoundError:
            pass
        project = self._client.read_project(project_name=target.project_name)
        try:
            # No trace_id: create_feedback must finish the HTTP write, not enqueue it.
            self._client.create_feedback(
                run_id=target.run_id,
                session_id=project.id,
                key="user_feedback",
                score=score,
                feedback_id=feedback_id,
                stop_after_attempt=1,
            )
        except LangSmithConflictError:
            self._client.update_feedback(feedback_id, score=score)

    async def save(self, target: FeedbackTarget, rating: Rating) -> None:
        try:
            async with asyncio.timeout(20):
                await asyncio.get_running_loop().run_in_executor(
                    self._workers, partial(self._save, target, rating)
                )
        except TimeoutError, LangSmithRequestTimeout:
            raise FeedbackTimeout() from None
        except Exception:
            raise FeedbackUnavailable() from None

    async def aclose(self) -> None:
        await asyncio.to_thread(self._workers.shutdown, wait=True, cancel_futures=True)
        await asyncio.to_thread(self._client.close)
