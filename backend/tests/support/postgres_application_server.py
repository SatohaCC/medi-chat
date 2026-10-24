"""Real OS application fixture: database only, external AI deliberately fixed."""

import os
import sys
from pathlib import Path

from backend.application.retrieval.queries.models import IntentResult


class FixedClassifier:
    def __init__(self, **kwargs):
        pass

    async def classify(self, request):
        return IntentResult(is_available=False)

    async def aclose(self):
        pass


class FixedKeywords:
    def __init__(self, **kwargs):
        pass

    def extract_keywords(self, text: str) -> tuple[str, ...]:
        return ("テスト",)


class FixedProvider:
    async def stream_response(self, messages, model=None):
        yield "テスト固定回答"


def create_server(*, real_morphology=False):
    def deny_inputs(event, args):
        if event == "sqlite3.connect":
            raise AssertionError("Runtime attempted SQLite access")
        if event == "open" and isinstance(args[0], (str, bytes)):
            path = str(args[0]).replace("\\", "/").lower()
            if "/data/pmda/" in path or Path(path).suffix in {
                ".xml",
                ".jsonl",
                ".sqlite3",
            }:
                raise AssertionError(
                    "Runtime attempted original/derived input file access"
                )

    sys.addaudithook(deny_inputs)
    from backend import main

    main.JevIntentClassifier = FixedClassifier
    if not real_morphology:
        main.JanomeKeywordExtractor = FixedKeywords
        main.get_janome_tokenizer = lambda: None
    return main.create_app(
        database_url=os.environ["TEST_RUNTIME_DATABASE_URL"],
        _database_schema=os.environ["PG_WORKER_SCHEMA"],
        llm_provider_factory=lambda _: FixedProvider(),
    )
