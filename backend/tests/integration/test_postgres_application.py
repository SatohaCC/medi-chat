"""PG-033/035/038: normal composition uses PostgreSQL snapshots for all reads."""

import asyncio
import importlib
import os
import socket
import subprocess
import sys
import time

import httpx
import pytest
from backend.application.retrieval.intent_contracts import IntentResult
from backend.tests.integration.test_postgres_registration import (
    pg_publisher as pg_publisher,
)
from backend.tests.integration.test_postgres_registration import publish
from backend.tests.support.paths import PROJECT_ROOT
from backend.tests.support.postgres_fixtures import pg_engines as pg_engines
from backend.tests.support.registration_oracles import source


class TestClassifier:
    __test__ = False

    def __init__(self, **kwargs):
        self.closed = False

    async def classify(self, request):
        return IntentResult(is_available=False)

    async def aclose(self):
        self.closed = True


class TestKeywords:
    __test__ = False

    def __init__(self, **kwargs):
        pass

    def extract_keywords(self, text: str) -> tuple[str, ...]:
        return ("テスト",)


class TestProvider:
    __test__ = False

    async def stream_response(self, messages, model=None):
        assert any("テストDB原文" in item["content"] for item in messages)
        yield "テスト回答"


@pytest.mark.asyncio
async def test_pg035_038_normal_app_has_snapshot_only_routes_and_owned_shutdown(
    pg_engines, pg_publisher, monkeypatch
):
    receipt = publish(pg_publisher, source("テストDB原文"))
    main = importlib.import_module("backend.main")
    monkeypatch.setattr(main, "JevIntentClassifier", TestClassifier)
    monkeypatch.setattr(main, "JanomeKeywordExtractor", TestKeywords)
    monkeypatch.setattr(main, "get_janome_tokenizer", lambda: None)
    app = main.create_app(
        database_url=os.environ["TEST_RUNTIME_DATABASE_URL"],
        _database_schema=pg_engines[2],
        llm_provider_factory=lambda _: TestProvider(),
    )
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client,
    ):
        acquired = []
        runtime = app.state.generation_runtime
        from contextlib import asynccontextmanager

        original = runtime.acquire

        @asynccontextmanager
        async def observed():
            async with original() as snapshot:
                acquired.append(snapshot.generation_id.value)
                yield snapshot

        runtime.acquire = observed
        for path in (
            "/health",
            "/api/medicines",
            "/api/medicines/autocomplete",
            "/api/search?q=テスト",
        ):
            before = len(acquired)
            response = await client.get(path)
            assert response.status_code == 200, response.text
            assert len(acquired) == before + 1, path
        assert response.json()["total_count"] == 1
        reply = await client.post(
            "/api/chat",
            json={"message": "警告", "product_yj_codes": ["111111111111"]},
        )
        assert reply.status_code == 200, reply.text
        assert reply.json()["answer"] == "テスト回答"
        assert (
            reply.json()["sources"][0]["unit_id"]
            == f"{receipt.document_id}:{receipt.source_sha256}:1"
        )
        assert len(set(acquired)) == 1
        assert not hasattr(app.state, "evidence_reader")
        assert app.state.database_engine.pool.checkedout() == 0
    assert app.state.intent_classifier.closed
    assert app.state.read_workers._closed


@pytest.mark.asyncio
async def test_pg033_real_process_without_input_access_restarts_from_db(
    pg_engines, pg_publisher, tmp_path
):

    receipt = publish(pg_publisher, source("テストDB原文"))
    isolated = tmp_path / "runtime-without-inputs"
    isolated.mkdir()
    assert not (isolated / "data/pmda").exists()
    environment = {
        **os.environ,
        "PYTHONPATH": str(PROJECT_ROOT),
        "PYTHONUTF8": "1",
        "PYTHON_DOTENV_DISABLED": "1",
        "MEDI_CHAT_DATABASE_URL": os.environ["TEST_RUNTIME_DATABASE_URL"],
        "PG_WORKER_SCHEMA": pg_engines[2],
    }
    for key in (
        "MEDI_CHAT_INDEX_PATH",
        "MEDI_CHAT_STRUCTURED_DIR",
        "MEDI_CHAT_IMPORT_DIR",
        "MEDI_CHAT_IMPORT_ROOT",
    ):
        environment.pop(key, None)
    for restart in range(2):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        with (tmp_path / f"server-{restart}.log").open("wb") as log:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "backend.tests.support.postgres_application_server:create_server",
                    "--factory",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                ],
                cwd=isolated,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            try:
                base = f"http://127.0.0.1:{port}"
                deadline = time.monotonic() + 20
                async with httpx.AsyncClient(base_url=base) as client:
                    while True:
                        assert process.poll() is None, (
                            tmp_path / f"server-{restart}.log"
                        ).read_text(encoding="utf-8")
                        try:
                            health = await client.get("/health")
                            if health.status_code == 200:
                                break
                        except httpx.TransportError:
                            pass
                        assert time.monotonic() < deadline
                        await asyncio.sleep(0.05)
                    assert health.json()["generation_id"] == receipt.generation_id
                    for path in (
                        "/api",
                        "/api/medicines",
                        "/api/medicines/autocomplete",
                        "/api/search?q=テスト",
                    ):
                        response = await client.get(path)
                        assert response.status_code == 200, response.text
                    result = await client.get(
                        f"/api/attachment-imports/{receipt.document_id}/{receipt.source_sha256}"
                    )
                    assert result.status_code == 200, result.text
                    answer = await client.post(
                        "/api/chat",
                        json={"message": "警告", "product_yj_codes": ["111111111111"]},
                    )
                    assert answer.status_code == 200, answer.text
                    assert answer.json()["answer"] == "テスト固定回答"
                    assert "テストDB原文" in answer.json()["sources"][0]["excerpt"]
            finally:
                process.terminate()
                await asyncio.to_thread(process.wait, 10)
