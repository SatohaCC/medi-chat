"""DBを使わず実ルーターで不正YJ入力の拒否を検証する。"""

from typing import Any

import pytest
from backend.application.chat.chat_service import ChatApplicationService
from backend.infrastructure.package_insert_definitions.loader import (
    get_package_insert_definitions,
)
from backend.presentation import chat_routes, chat_websocket_routes, search_routes
from backend.presentation.chat_service import AppChatService
from backend.presentation.dependencies import get_chat_service
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(chat_routes.router)
    app.include_router(chat_websocket_routes.router)
    app.include_router(search_routes.router)

    class UnusedDependency:
        is_available = False

        async def read_medicines(self):
            raise AssertionError("invalid input must be rejected before reading")

    unused = UnusedDependency()
    definitions = get_package_insert_definitions()
    dependencies: dict[str, Any] = {
        "medicine_reader": unused,
        "evidence_reader": unused,
        "intent_classifier": unused,
        "keyword_extractor": unused,
        "intent_policy": definitions.intent_policy,
        "answer_prompt_policy": definitions.answer_prompt_policy,
        "provider_factory": lambda _: unused,
    }
    application = ChatApplicationService(**dependencies)
    service = AppChatService(**dependencies, application_service=application)
    app.dependency_overrides[get_chat_service] = lambda: service
    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize("code", ["short", "1234567-0000", "1234567A00000"])
def test_rest_chat_and_search_reject_invalid_yj(client, code):
    assert (
        client.post(
            "/api/chat", json={"message": "テスト質問", "product_yj_codes": [code]}
        ).status_code
        == 422
    )
    assert (
        client.get("/api/search", params={"q": "テスト", "yj_codes": code}).status_code
        == 422
    )


def test_websocket_rejects_invalid_yj_and_keeps_connection(client):
    with client.websocket_connect("/ws/chat") as socket:
        socket.send_json(
            {
                "type": "message",
                "product_yj_codes": ["short"],
                "messages": [{"role": "user", "content": "テスト質問"}],
            }
        )
        response = socket.receive_json()
        while response["type"] == "retrieval_status":
            response = socket.receive_json()
        assert response["type"] == "error"
        assert response["content"] == "Invalid product_yj_codes"
        socket.send_json({"type": "ping"})
        assert socket.receive_json() == {"type": "pong"}


@pytest.mark.parametrize("value", [12, True, None, {}, []])
def test_presentation_rejects_non_string_codes(client, value):
    assert (
        client.post(
            "/api/chat", json={"message": "テスト", "product_yj_codes": [value]}
        ).status_code
        == 422
    )


def test_presentation_dto_accepts_strings_without_domain_format_validation():
    payload = chat_routes.ChatRequest(message="テスト", product_yj_codes=["short"])
    assert payload.product_yj_codes == ["short"]
