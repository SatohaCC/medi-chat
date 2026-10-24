import pytest
from backend.tests.application.retrieval.test_selected_medicines import (
    NoJev,
    NoKeywords,
)
from backend.tests.integration.test_chat_service import RecordingProvider
from backend.tests.support.chat_service import compose_chat_service
from backend.tests.support.postgres_fixtures import pg_api as pg_api
from backend.tests.support.postgres_fixtures import pg_engines as pg_engines
from fastapi.testclient import TestClient


@pytest.mark.parametrize("codes", [[], ["1234567A0000"], ["9999999A0000"]])
@pytest.mark.parametrize("transport", ["rest", "/api/ws", "/ws/chat"])
def test_only_selected_codes_are_used_and_connections_are_released(
    pg_api, codes, transport
):
    provider = RecordingProvider()
    app = pg_api(llm_provider_factory=lambda _: provider)
    with TestClient(app) as client:
        app.state.chat_service = compose_chat_service(
            app.state.chat_service,
            intent_classifier=NoJev(),
            keyword_extractor=NoKeywords(),
        )
        message = "テスト薬とロキソニンの副作用について"
        if transport == "rest":
            response = client.post(
                "/api/chat", json={"message": message, "product_yj_codes": codes}
            )
            if not codes:
                assert response.status_code == 422
                assert provider.calls == []
                assert app.state.database_engine.pool.checkedout() == 0
                return
            assert response.status_code == 200
            payload = response.json()
            sources = payload["sources"]
            assert payload["needs_clarification"] == (codes != ["1234567A0000"])
        else:
            with client.websocket_connect(transport) as ws:
                ws.send_json(
                    {
                        "type": "message",
                        "request_id": "a871f25a-1eb7-4c5e-8c6e-4511dce60280",
                        "messages": [{"role": "user", "content": message}],
                        "product_yj_codes": codes,
                    }
                )
                sources = []
                while True:
                    event = ws.receive_json()
                    if not codes:
                        assert event["type"] == "error"
                        assert "product_yj_codes" in event["content"]
                        break
                    assert event["type"] != "error", event
                    if event["type"] == "sources":
                        sources = event["sources"]
                    if event["type"] == "text_done":
                        break
                ws.send_json(
                    {"type": "ping", "ping_id": "a871f25a-1eb7-4c5e-8c6e-4511dce60280"}
                )
                assert ws.receive_json() == {
                    "type": "pong",
                    "ping_id": "a871f25a-1eb7-4c5e-8c6e-4511dce60280",
                }
        if codes == ["1234567A0000"]:
            assert sources
            assert all(source["product_yj_codes"] == codes for source in sources)
            assert len(provider.calls) == 1
        else:
            assert sources == []
            assert provider.calls == []
        assert app.state.database_engine.pool.checkedout() == 0
