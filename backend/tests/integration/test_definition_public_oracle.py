"""TC20: whole REST/WS observations with real temporary storage and fixed SDK doubles."""

import json
from copy import deepcopy
from unittest.mock import patch

from backend.tests.integration.test_interaction_xml_oracle import ORACLE as XML_ORACLE
from backend.tests.integration.test_interaction_xml_oracle import (
    assert_public_source,
    major_expectations,
)
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


def test_tc20_public_envelope_is_stable_and_current_content_matches_originals() -> None:
    expected = json.loads(REFERENCE.read_text(encoding="utf-8"))
    actual = observe_public()
    assert actual["unknown"] == expected["unknown"]
    for label in ("single", "multiple"):
        case = actual[label]
        assert isinstance(case, dict)
        sources = case["rest"]["sources"]
        documents = XML_ORACLE[:1] if label == "single" else XML_ORACLE[:2]
        indexed = {
            identifier: (document, code)
            for identifier, document, code in major_expectations(documents)
        }
        assert [source["unit_id"] for source in sources] == list(indexed)
        for source in sources:
            document, code = indexed[source["unit_id"]]
            assert_public_source(source, document, code)
            expected_routes = ["logic", "jev"]
            if document is not XML_ORACLE[0] and code == "10":
                expected_routes.append("keyword")
            assert source["retrieved_by"] == expected_routes
        previous_ids = set()
        for event in case["ws"]:
            if event["type"] == "sources":
                ids = {source["unit_id"] for source in event["sources"]}
                assert previous_ids <= ids <= set(indexed)
                previous_ids = ids
                for source in event["sources"]:
                    document, code = indexed[source["unit_id"]]
                    assert_public_source(source, document, code)
        assert previous_ids == set(indexed)
        for messages in case["provider_messages"]:
            assert messages[1:] == [{"role": "user", "content": "相互作用は？"}]
            for source in sources:
                assert f"単位ID: {source['unit_id']}" in messages[0]["content"]
                assert source["excerpt"] in messages[0]["content"]
        assert case["rest"]["answer"] == "\n".join(
            message["content"] for message in case["provider_messages"][0]
        )
        expected_text = "\n".join(
            message["content"] for message in case["provider_messages"][1]
        )
        assert (
            "".join(
                event["content"]
                for event in case["ws"]
                if event["type"] == "text_delta"
            )
            == expected_text
        )

        def envelope(value):
            value = deepcopy(value)
            value["rest"]["sources"] = []
            value["rest"]["answer"] = "verified against original sources"
            for event in value["ws"]:
                if event["type"] == "sources":
                    event["sources"] = []
                if event["type"] == "text_delta":
                    event["content"] = "verified against provider input"
            events = []
            for event in value["ws"]:
                if (
                    event["type"] == "sources"
                    and events
                    and events[-1]["type"] == "sources"
                ):
                    continue
                events.append(event)
            value["ws"] = events
            for messages in value["provider_messages"]:
                messages[0]["content"] = messages[0]["content"].split("[根拠 ")[0]
            return value

        assert envelope(case) == envelope(expected[label])
