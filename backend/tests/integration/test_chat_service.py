"""共通の会話処理とREST / WebSocketの契約を検証する。"""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from backend.application.chat.llm_contracts import LLMProvider
from backend.application.medicine.product_models import ResolvedMedicine
from backend.application.retrieval.retrieve_evidence import _search_evidence
from backend.domain.medicine.value_objects import MedicineMatch as DomainMedicineMatch
from backend.domain.retrieval.primitives import (
    DetectionSource,
    SearchKeyword,
    SearchSectionCode,
)
from backend.domain.retrieval.value_objects import SearchCriteria
from backend.infrastructure.intent.jev_classifier import JevIntentClassifier
from backend.infrastructure.morphology.janome_keyword_extractor import (
    JanomeKeywordExtractor,
)
from backend.infrastructure.package_insert_definitions.loader import (
    get_package_insert_definitions,
)
from backend.infrastructure.persistence.evidence_reader import SqlAlchemyEvidenceReader
from backend.infrastructure.persistence.index_writer import SqlAlchemyIndexWriter
from backend.infrastructure.persistence.medicine_reader import SqlAlchemyMedicineReader
from backend.infrastructure.persistence.sqlite_engine import create_sqlite_engine
from backend.infrastructure.sources.file_index_source import FileIndexSourceReader
from backend.main import create_app
from backend.presentation.chat_models import ChatMessage
from backend.presentation.chat_service import AppChatService
from backend.tests.infrastructure.persistence.test_alembic_migrations import (
    _migrate_database,
)
from backend.tests.support.storage_fixtures import (
    build_document_store,
    make_search_payload,
    write_structured_document,
)
from fastapi.testclient import TestClient
from sqlalchemy.engine import URL


class RecordingProvider(LLMProvider):
    def __init__(self) -> None:
        self.calls: list[tuple[list[dict[str, str]], str | None]] = []

    async def stream_response(
        self, messages: list[dict[str, str]], model: str | None = None
    ) -> AsyncIterator[str]:
        self.calls.append((messages, model))
        yield "同じ"
        yield "回答"


def test_RESTとWebSocketで回答と根拠とLLM入力が一致する(tmp_path: Path) -> None:
    structured = write_structured_document(tmp_path)
    index_path = tmp_path / "index.sqlite3"
    _migrate_database(index_path, structured)
    engine = create_sqlite_engine(
        URL.create("sqlite", database=index_path.as_posix()).render_as_string(
            hide_password=False
        )
    )
    try:
        SqlAlchemyIndexWriter(engine).replace(
            FileIndexSourceReader(structured).read_snapshot()
        )
    finally:
        engine.dispose()
    from backend.tests.support.registration_runtime_fixtures import (
        register_synthetic_prepared_index,
    )

    register_synthetic_prepared_index(structured, index_path)
    provider = RecordingProvider()
    app = create_app(
        structured,
        index_path,
        lambda _: provider,
        import_directory=tmp_path / "imports",
    )
    with (
        patch.dict(os.environ, {"TYPESAFE_API_KEY": "", "JEV_API_KEY": ""}),
        TestClient(app) as client,
    ):
        rest = client.post(
            "/api/chat",
            json={
                "message": "副作用の頭痛について",
                "product_yj_codes": ["1234567A0000"],
                "provider": "openai",
                "model": "gpt-6-luna",
            },
        )
        with client.websocket_connect("/api/ws") as socket:
            socket.send_json(
                {
                    "type": "message",
                    "messages": [{"role": "user", "content": "副作用の頭痛について"}],
                    "product_yj_codes": ["1234567A0000"],
                    "provider": "openai",
                    "model": "gpt-6-luna",
                }
            )
            events = []
            while True:
                event = socket.receive_json()
                events.append(event)
                if event["type"] == "text_done":
                    break
    assert rest.status_code == 200
    assert (
        rest.json()["answer"]
        == "同じ回答"
        == "".join(
            event["content"] for event in events if event["type"] == "text_delta"
        )
    )
    source_events = [event for event in events if event["type"] == "sources"]
    assert rest.json()["sources"] == source_events[-1]["sources"]
    assert len(source_events) >= 2

    assert len(provider.calls) == 2
    assert provider.calls[0] == provider.calls[1]
    assert [event["type"] for event in events] == [
        "retrieval_status",
        *["sources"] * len(source_events),
        "text_delta",
        "text_delta",
        "text_done",
    ]


@pytest.mark.asyncio
async def test_対象薬が見つからない場合はLLMを作成しない(tmp_path: Path) -> None:
    structured = write_structured_document(tmp_path)
    build_document_store(structured, tmp_path / "index.sqlite3")
    factory = Mock(side_effect=AssertionError("LLMを作成してはいけない"))
    with patch.dict(os.environ, {"TYPESAFE_API_KEY": "", "JEV_API_KEY": ""}):
        engine = create_sqlite_engine(
            URL.create(
                "sqlite", database=(tmp_path / "index.sqlite3").as_posix()
            ).render_as_string(hide_password=False)
        )
        catalog = get_package_insert_definitions()
        service = AppChatService(
            medicine_reader=SqlAlchemyMedicineReader(engine),
            evidence_reader=SqlAlchemyEvidenceReader(engine),
            intent_classifier=JevIntentClassifier(),
            keyword_extractor=JanomeKeywordExtractor(
                search_policy=catalog.text_search_policy,
                morphology_settings=catalog.morphology_settings,
            ),
            intent_policy=catalog.intent_policy,
            answer_prompt_policy=catalog.answer_prompt_policy,
            provider_factory=factory,
        )
        messages = [ChatMessage(role="user", content="副作用について")]
        reply = await service.prepare_reply(messages, ["0000000A0000"])
        chunks = [chunk async for chunk in service.stream_answer(reply, messages)]
    assert reply.needs_clarification
    assert "YJコード" in reply.answer
    assert chunks == [reply.answer]
    factory.assert_not_called()
    engine.dispose()


def test_三種類の検索結果は件数を制限せず重複だけを除く(tmp_path: Path) -> None:
    structured = write_structured_document(tmp_path, unit_count=40)
    build_document_store(structured, tmp_path / "index.sqlite3")
    sources = search_sources(
        tmp_path / "index.sqlite3",
        ["test_001"],
        [
            SearchCriteria(
                source=DetectionSource("logic"),
                section_codes=(SearchSectionCode("11.1"),),
            ),
            SearchCriteria(
                source=DetectionSource("jev"),
                section_codes=(SearchSectionCode("11.1"),),
            ),
            SearchCriteria(
                source=DetectionSource("keyword"), keywords=(SearchKeyword("頭痛"),)
            ),
        ],
    )
    assert len(sources) == 40
    assert [source.unit_id.value for source in sources] == [
        f"test_001:{index:03d}" for index in range(40)
    ]
    assert {source.retrieved_by for source in sources} == {
        frozenset(["logic", "jev", "keyword"])
    }


def test_重複はunit_idだけで除去し固有unitと取得元を保持する(tmp_path: Path) -> None:
    structured = write_structured_document(tmp_path, unit_count=4)
    path = structured / "test_001" / "search_units.jsonl"
    units = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    definitions = [
        ("1", "警告の原見出し", "頭痛の同じ原文"),
        ("10.1", "併用禁忌の原見出し", "個別unitの同じ原文"),
        ("16.7", "薬物相互作用の原見出し", "個別unitの同じ原文"),
        ("11.1", "重大な副作用の原見出し", "頭痛の同じ原文"),
    ]
    for unit, (code, title, text) in zip(units, definitions, strict=True):
        unit["section"] = {"code": code, "title": title}
        unit["text"] = text
    path.write_text(
        "\n".join(
            json.dumps(make_search_payload(unit), ensure_ascii=False) for unit in units
        ),
        encoding="utf-8",
    )
    build_document_store(structured, tmp_path / "index.sqlite3")

    sources = search_sources(
        tmp_path / "index.sqlite3",
        ["test_001"],
        [
            SearchCriteria(
                source=DetectionSource("logic"),
                section_codes=(SearchSectionCode("1"), SearchSectionCode("10.1")),
            ),
            SearchCriteria(
                source=DetectionSource("jev"),
                section_codes=(SearchSectionCode("1"), SearchSectionCode("16.7")),
            ),
            SearchCriteria(
                source=DetectionSource("keyword"), keywords=(SearchKeyword("頭痛"),)
            ),
        ],
    )

    assert len(sources) == 4
    assert {source.unit_id.value: source.retrieved_by for source in sources} == {
        "test_001:000": frozenset(["logic", "jev", "keyword"]),
        "test_001:001": frozenset({"logic"}),
        "test_001:002": frozenset({"jev"}),
        "test_001:003": frozenset({"keyword"}),
    }
    assert {source.unit_id.value: source.excerpt for source in sources} == {
        "test_001:000": "頭痛の同じ原文",
        "test_001:001": "個別unitの同じ原文",
        "test_001:002": "個別unitの同じ原文",
        "test_001:003": "頭痛の同じ原文",
    }


def search_sources(
    index_path: Path, document_ids: list[str], criteria: list[SearchCriteria]
):
    engine = create_sqlite_engine(
        URL.create("sqlite", database=index_path.as_posix()).render_as_string(
            hide_password=False
        )
    )
    try:
        medicines = (
            ResolvedMedicine(
                medicine=DomainMedicineMatch(
                    generic_name="テスト成分",
                    brand_names=("テスト薬",),
                    yj_codes=("1234567A0000",),
                ),
                document_ids=tuple(document_ids),
            ),
        )
        return asyncio.run(
            _search_evidence(SqlAlchemyEvidenceReader(engine), medicines, criteria)
        )
    finally:
        engine.dispose()
