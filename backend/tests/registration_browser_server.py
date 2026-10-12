"""Real main routes/readers; only detector/LLM SDKs are deterministic doubles."""

import argparse
import json
from collections.abc import AsyncIterator
from pathlib import Path

import uvicorn
from backend import main
from backend.application.retrieval.intent_contracts import IntentRequest, IntentResult
from backend.infrastructure.intent.jev_classifier import JevIntentClassifier
from backend.infrastructure.morphology.janome_keyword_extractor import (
    JanomeKeywordExtractor,
)

_metrics_path: Path | None = None
_metrics: dict[str, object] = {"factory_calls": 0, "stream_calls": 0, "questions": []}


def record(key: str, question: str | None = None) -> None:
    if question is None:
        value = _metrics[key]
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
        return IntentResult(is_available=False)


class FixedKeywords(JanomeKeywordExtractor):
    def extract_keywords(self, text: str) -> tuple[str, ...]:
        return ()


class FixedProvider:
    async def stream_response(
        self, messages: list[dict[str, str]], model: str | None = None
    ) -> AsyncIterator[str]:
        record("stream_calls")
        yield "固定SDK回答（通信なし）"


def provider_factory(name: str | None) -> FixedProvider:
    record("factory_calls")
    return FixedProvider()


def run() -> None:
    global _metrics_path
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--metrics-file", type=Path)
    args = parser.parse_args()
    _metrics_path = args.metrics_file
    main.JevIntentClassifier = FixedClassifier
    main.JanomeKeywordExtractor = FixedKeywords
    app = main.create_app(
        args.root / "structured",
        args.root / "index.sqlite3",
        provider_factory,
        import_directory=args.root / "imports",
    )
    uvicorn.run(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    run()
