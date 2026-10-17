"""TC20: whole REST/WS observations with real temporary storage and fixed SDK doubles."""

import json
from unittest.mock import patch

from backend.tests.integration.test_interaction_xml_oracle import ORACLE as XML_ORACLE
from backend.tests.presentation import test_api_routes as api_fixture
from backend.tests.support.paths import FIXTURES_ROOT
from fastapi import FastAPI

REFERENCE = FIXTURES_ROOT / "definition-public-reference.json"


def observe_public() -> dict[str, object]:
    fixture = api_fixture.ChatApiRouteTests
    fixture.setUpClass()
    try:
        application = fixture.client.app
        assert isinstance(application, FastAPI)
        service = application.state.chat_service
        results = {}
        # Use the same stored XML pair as the existing full-field evidence oracle.
        selected = XML_ORACLE
        for label, codes in (
            ("single", [selected[0]["yj"]]),
            ("multiple", [selected[0]["yj"], selected[1]["yj"]]),
            ("unknown", ["999999999999"]),
        ):
            provider = api_fixture.PromptEchoProvider()
            with (
                patch.object(
                    service,
                    "intent_classifier",
                    api_fixture.InteractionIntentClassifier(),
                ),
                patch.object(
                    service, "keyword_extractor", api_fixture.InteractionKeywords()
                ),
                patch.object(
                    service, "provider_factory", lambda _, current=provider: current
                ),
            ):
                response = fixture.client.post(
                    "/api/chat",
                    json={"message": "相互作用は？", "product_yj_codes": codes},
                )
                with fixture.client.websocket_connect("/api/ws") as socket:
                    socket.send_json(
                        {
                            "type": "message",
                            "messages": [{"role": "user", "content": "相互作用は？"}],
                            "product_yj_codes": codes,
                        }
                    )
                    events = []
                    while True:
                        event = socket.receive_json()
                        events.append(event)
                        if event["type"] in ("text_done", "error"):
                            break
            results[label] = {
                "status": response.status_code,
                "rest": response.json(),
                "ws": events,
                "provider_messages": provider.calls,
            }
        return results
    finally:
        fixture.tearDownClass()


def test_tc20_full_public_payload_matches_prechange_oracle() -> None:
    expected = json.loads(REFERENCE.read_text(encoding="utf-8"))
    assert observe_public() == expected
