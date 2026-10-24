"""Real main routes/readers; only detector/LLM SDKs are deterministic doubles."""

import argparse
import asyncio
import json
import os
from collections.abc import AsyncIterator
from pathlib import Path

import uvicorn
from backend.application.retrieval.queries.models import IntentRequest, IntentResult
from backend.infrastructure.intent.jev_classifier import JevIntentClassifier
from backend.infrastructure.morphology.janome_keyword_extractor import (
    JanomeKeywordExtractor,
)
from backend.tests.support.authentication import (
    SignedTestActor,
    authentication_environment,
)
from backend.tests.support.postgres_browser_fixture import fixture_schema, selected_url

_metrics_path: Path | None = None
_ws_lifetime = False
_metrics: dict[str, object] = {"factory_calls": 0, "stream_calls": 0, "questions": []}


def record(key: str, question: str | None = None) -> None:
    if question is None:
        value = _metrics.get(key, 0)
        assert isinstance(value, int)
        _metrics[key] = value + 1
    else:
        questions = _metrics["questions"]
        assert isinstance(questions, list)
        questions.append(question)
    if _metrics_path is not None:
        _metrics_path.write_text(
            json.dumps(_metrics, ensure_ascii=False), encoding="utf-8"
        )


class FixedClassifier(JevIntentClassifier):
    async def classify(self, request: IntentRequest) -> IntentResult:
        record("questions", request.question)
        if _ws_lifetime and "[テスト準備待機]" in request.question:
            record("preparation_started")
            try:
                await asyncio.Event().wait()
            finally:
                record("preparation_closed")
        return IntentResult(is_available=False)


class FixedKeywords(JanomeKeywordExtractor):
    def extract_keywords(self, text: str) -> tuple[str, ...]:
        return ()


class FixedProvider:
    async def stream_response(
        self, messages: list[dict[str, str]], model: str | None = None
    ) -> AsyncIterator[str]:
        record("stream_calls")
        if _ws_lifetime and "[テスト無音]" in messages[-1]["content"]:
            record("silent_started")
            try:
                yield "部分テスト回答"
                await asyncio.Event().wait()
            finally:
                record("silent_closed")
            return
        yield "固定SDK回答（通信なし）"


def provider_factory(name: str | None) -> FixedProvider:
    record("factory_calls")
    return FixedProvider()


def run() -> None:
    global _metrics_path, _ws_lifetime
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--metrics-file", type=Path)
    parser.add_argument("--ws-lifetime", action="store_true")
    args = parser.parse_args()
    _metrics_path = args.metrics_file
    _ws_lifetime = args.ws_lifetime
    os.environ["MEDI_CHAT_DATABASE_URL"] = selected_url()
    os.environ.update(authentication_environment())
    os.environ.pop("AUTH_PRIVATE_KEY_FILE", None)
    from backend import main

    main.JevIntentClassifier = FixedClassifier
    main.JanomeKeywordExtractor = FixedKeywords
    app = main.create_app(
        database_url=selected_url(),
        _database_schema=fixture_schema(args.root),
        llm_provider_factory=provider_factory,
    )
    app.add_middleware(SignedTestActor)
    uvicorn.run(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    run()
