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
    service = AppChatService(application_service=application)
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


@pytest.mark.parametrize(
    "second", ["1234567A0000", " 1234567A0000 ", "１２３４５６７Ａ００００"]
)
def test_all_input_routes_reject_duplicate_normalized_codes(client, second):
    codes = ["1234567A0000", second]
    response = client.post(
        "/api/chat", json={"message": "テスト質問", "product_yj_codes": codes}
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "product_yj_codes must not contain duplicates"
    response = client.get("/api/search", params={"q": "テスト", "yj_codes": codes})
    assert response.status_code == 422
    with client.websocket_connect("/ws/chat") as socket:
        socket.send_json(
            {
                "type": "message",
                "product_yj_codes": codes,
                "messages": [{"role": "user", "content": "テスト質問"}],
            }
        )
        response = socket.receive_json()
        while response["type"] == "retrieval_status":
            response = socket.receive_json()
        assert response["type"] == "error"
        assert response["content"] == "product_yj_codes must not contain duplicates"
        socket.send_json({"type": "ping"})
        assert socket.receive_json() == {"type": "pong"}


@pytest.fixture
def unavailable_client():
    app = FastAPI()
    app.include_router(search_routes.router)
    app.include_router(chat_websocket_routes.router)
    app.dependency_overrides[get_chat_service] = lambda: None
    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize(
    "codes,error",
    [
        (["short"], "Invalid product_yj_codes"),
        (
            ["1234567A0000", " 1234567A0000 "],
            "product_yj_codes must not contain duplicates",
        ),
        (
            ["1234567A0000", "１２３４５６７Ａ００００"],
            "product_yj_codes must not contain duplicates",
        ),
    ],
)
def test_unavailable_service_still_rejects_invalid_codes(
    unavailable_client, codes, error
):
    response = unavailable_client.get(
        "/api/search", params={"q": "テスト", "yj_codes": codes}
    )
    assert response.status_code == 422
    assert response.json()["detail"] == error
    with unavailable_client.websocket_connect("/ws/chat") as socket:
        socket.send_json(
            {
                "type": "message",
                "product_yj_codes": codes,
                "messages": [{"role": "user", "content": "テスト質問"}],
            }
        )
        assert socket.receive_json() == {"type": "error", "content": error}
        socket.send_json({"type": "ping"})
        assert socket.receive_json() == {"type": "pong"}


def test_unavailable_service_preserves_valid_input_responses(unavailable_client):
    for codes in ([], ["1234567A0000"]):
        response = unavailable_client.get(
            "/api/search", params={"q": "テスト", "yj_codes": codes}
        )
        assert response.status_code == 200
        assert response.json()["items"] == []
    with unavailable_client.websocket_connect("/ws/chat") as socket:
        socket.send_json(
            {
                "type": "message",
                "product_yj_codes": ["1234567A0000"],
                "messages": [{"role": "user", "content": "テスト質問"}],
            }
        )
        assert socket.receive_json() == {
            "type": "error",
            "content": "Medicine corpus is not ready",
        }
