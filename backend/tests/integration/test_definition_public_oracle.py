"""TC20: whole REST/WS observations with real temporary storage and fixed SDK doubles."""

import html
import json
import re
from copy import deepcopy
from unittest.mock import patch
from xml.etree import ElementTree as ET

import pytest
from backend.tests.integration.test_interaction_xml_oracle import (
    assert_public_source,
    get_interaction_oracle,
    major_expectations,
)
from backend.tests.presentation import test_api_routes as api_fixture
from backend.tests.support.chat_service import compose_chat_service
from backend.tests.support.paths import FIXTURES_ROOT, PROJECT_ROOT
from backend.tests.support.section_records import major_unit_id
from fastapi import FastAPI

pytestmark = [pytest.mark.postgres, pytest.mark.source_data]


REFERENCE = FIXTURES_ROOT / "definition-public-reference.json"


def indication_originals(documents):
    originals = {}
    for document in documents:
        path = next(
            (PROJECT_ROOT / "data/pmda/originals").glob(
                f"*/{document['document_id']}.xml"
            )
        )
        root = ET.parse(path).getroot()
        for code, tag in (
            ("4", "IndicationsOrEfficacy"),
            ("5", "EfficacyRelatedPrecautions"),
        ):
            for node in root.iter():
                if node.tag.rsplit("}", 1)[-1] != tag:
                    continue
                texts = [
                    leaf.text
                    for leaf in node.iter()
                    if leaf.tag.rsplit("}", 1)[-1] == "Lang"
                    and not len(leaf)
                    and leaf.text
                    and leaf.text.strip()
                ]
                if texts:
                    originals[major_unit_id(document, code)] = (document, code, texts)
    return originals


def assert_expanded_source(source, document, code, originals):
    if code not in {"4", "5"}:
        assert_public_source(source, document, code)
        return
    assert source["unit_id"] == major_unit_id(document, code)
    for key in ("document_id", "product_name", "generic_name"):
        assert source[key] == document[key]
    assert source["product_yj_codes"] == [document["yj"]]
    assert source["section"]["code"] == code
    assert (
        source["section"]["title"]
        == {"4": "効能又は効果", "5": "効能又は効果に関連する注意"}[code]
    )
    assert source["document_revision"] == document["revision"]
    assert source["kind"] == "section"
    body = "".join(html.unescape(re.sub(r"<[^>]+>", "", source["excerpt"])).split())
    for text in originals[source["unit_id"]][2]:
        assert "".join(text.split()) in body


def observe_public() -> dict[str, object]:
    fixture = api_fixture.ChatApiRouteTests
    fixture.setUpClass()
    try:
        application = fixture.client.app
        assert isinstance(application, FastAPI)
        service = application.state.chat_service
        results = {}
        # Use the same stored XML pair as the existing full-field evidence oracle.
        selected = get_interaction_oracle()
        for label, codes in (
            ("single", [selected[0]["yj"]]),
            ("multiple", [selected[0]["yj"], selected[1]["yj"]]),
            ("unknown", ["999999999999"]),
        ):
            provider = api_fixture.PromptEchoProvider()
            with (
                patch.object(
                    application.state,
                    "chat_service",
                    compose_chat_service(
                        service,
                        intent_classifier=api_fixture.InteractionIntentClassifier(),
                        keyword_extractor=api_fixture.InteractionKeywords(),
                        provider_factory=lambda _, current=provider: current,
                    ),
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
                            "request_id": "a871f25a-1eb7-4c5e-8c6e-4511dce60280",
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
        documents = (
            get_interaction_oracle()[:1]
            if label == "single"
            else get_interaction_oracle()[:2]
        )
        indexed = {
            identifier: (document, code)
            for identifier, document, code in major_expectations(documents)
        }
        # 「相互作用」は「作用」にも一致するため、4/5の原本も独立に照合する。
        originals = indication_originals(documents)
        indexed.update(
            {
                identifier: (doc, code)
                for identifier, (doc, code, _) in originals.items()
            }
        )
        indexed = dict(
            sorted(indexed.items(), key=lambda item: (int(item[1][1]), item[0]))
        )
        assert [source["unit_id"] for source in sources] == list(indexed)
        for source in sources:
            document, code = indexed[source["unit_id"]]
            assert_expanded_source(source, document, code, originals)
            expected_routes = ["logic"] if code in {"4", "5"} else ["logic", "jev"]
            if document is not get_interaction_oracle()[0] and code == "10":
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
                    assert_expanded_source(source, document, code, originals)
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
