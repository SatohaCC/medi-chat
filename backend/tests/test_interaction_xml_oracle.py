"""TC120–123: fixed original-XML oracle versus real registration/runtime/prompt."""

import asyncio
import copy
import json
import sqlite3
import time
from contextlib import closing
from html.parser import HTMLParser
from pathlib import Path

import pytest
from backend.application.chat.answer_question import answer_question
from backend.application.chat.chat_models import ChatMessage
from backend.application.indexing.medicine_catalog import AttachmentProductCatalog
from backend.application.retrieval.intent_contracts import IntentResult
from backend.application.retrieval.retrieve_evidence import retrieve_evidence
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.retrieval.primitives import (
    DetectionSource,
    IntentName,
    Probability,
    SearchSectionCode,
)
from backend.domain.retrieval.value_objects import IntentCandidate, SearchCriteria
from backend.infrastructure.package_insert_definitions.loader import (
    get_package_insert_definitions,
)
from backend.infrastructure.persistence.generation_runtime import GenerationRuntime
from backend.infrastructure.persistence.read_workers import ReadWorkers
from backend.tests.interaction_raw_oracle import DOCUMENTS, ROOT, read_raw_oracle
from backend.tests.test_alembic_migrations import _migrate_database
from backend.tests.test_registration_publisher import (
    FileAttachmentImportStore,
    SqliteRegistrationPublisher,
    publish,
)

FIXTURE = Path(__file__).parent / "fixtures/interaction_oracle_v6.json"
ORACLE = json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def registered_publisher(tmp_path_factory):
    root = tmp_path_factory.mktemp("interaction-oracle")
    index = root / "copy.sqlite3"
    _migrate_database(index, root)
    publisher = SqliteRegistrationPublisher(
        index, FileAttachmentImportStore(root / "imports")
    )
    for doc, _, _ in DOCUMENTS:
        publish(
            publisher,
            next((ROOT / "data/pmda/originals").glob(f"*/{doc}.xml")).read_bytes(),
        )
    return publisher


class Cells(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.cell = None
        self.row = None
        self.paragraph = None
        self.paragraphs = []

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag == "td":
            self.cell = ""
        elif tag == "p":
            self.paragraph = ""
        elif tag == "br":
            if self.cell is not None:
                self.cell += "\n"
            elif self.paragraph is not None:
                self.paragraph += "\n"

    def handle_data(self, data):
        if self.cell is not None:
            self.cell += data
        elif self.paragraph is not None:
            self.paragraph += data

    def handle_endtag(self, tag):
        if tag == "td":
            assert self.row is not None and self.cell is not None
            self.row.append(self.cell)
            self.cell = None
        elif tag == "tr" and self.row:
            self.rows.append(self.row)
        elif tag == "p":
            assert self.paragraph is not None
            self.paragraphs.append(self.paragraph)
            self.paragraph = None


def assert_source(source, document, code):
    assert_public_source(source.to_dict(), document, code)


def assert_public_source(source, document, code):
    expected = document["sections"][code]
    assert set(source) == {
        "unit_id",
        "document_id",
        "product_name",
        "generic_name",
        "product_yj_codes",
        "document_revision",
        "section",
        "kind",
        "excerpt",
        "columns",
        "references",
        "url",
        "retrieved_by",
    }
    assert source["unit_id"] == expected["unit_id"]
    assert source["document_id"] == document["document_id"]
    assert source["product_name"] == document["product_name"]
    assert source["generic_name"] == document["generic_name"]
    assert source["document_revision"] == document["revision"]
    assert source["product_yj_codes"] == [document["yj"]]
    assert source["section"]["code"] == code
    assert (
        source["section"]["title"]
        == {
            "10": "相互作用",
            "10.1": "併用禁忌",
            "10.2": "併用注意",
            "16.7": "薬物相互作用",
        }[code]
    )
    parser = Cells()
    parser.feed(source["excerpt"])
    assert parser.rows == expected["rows"]
    assert parser.paragraphs == expected["body"]
    actual_refs = source["references"]
    expected_refs = expected["references"]
    assert actual_refs == expected_refs
    assert (
        source["url"]
        == f"https://www.pmda.go.jp/PmdaSearch/iyakuDetail/{document['document_id']}"
    )
    assert source["kind"] == "section"
    assert source["columns"] is None


def assert_public_collection(sources, pair):
    documents = ORACLE if pair else ORACLE[:1]
    expected = sorted(
        [
            (doc["sections"][code]["unit_id"], doc, code)
            for doc in documents
            for code in doc["sections"]
        ],
        key=lambda item: (tuple(int(part) for part in item[2].split(".")), item[0]),
    )
    assert [source["unit_id"] for source in sources] == [item[0] for item in expected]
    for source, (_, doc, code) in zip(sources, expected, strict=True):
        assert_public_source(source, doc, code)
        routes = ["logic", "jev"]
        if pair and doc["document_id"] != DOCUMENTS[0][0] and code == "10.1":
            routes.append("keyword")
        assert source["retrieved_by"] == routes


def test_tc121_fixed_fixture_matches_original_xml_and_detects_swapped_columns_targets():
    assert read_raw_oracle() == ORACLE
    altered = copy.deepcopy(ORACLE)
    row = altered[0]["sections"]["10.1"]["rows"][0]
    row[0], row[1] = row[1], row[0]
    assert altered != read_raw_oracle()
    altered = copy.deepcopy(ORACLE)
    altered[0]["sections"]["10.1"]["references"][0]["target_section_code"] = "16.7.2"
    assert altered != read_raw_oracle()


def stored_reference_positions(tree):
    records = []
    language_counts = {}
    reference_counts = {}

    def visit(node, owner=None, language=None):
        tag = node["tag"]
        if tag == "Item":
            owner = node["attributes"]["id"]
        if tag == "Lang" and owner is not None:
            language = language_counts.get(owner, 0)
            language_counts[owner] = language + 1
        if tag.endswith("Ref"):
            slot = (owner, language)
            index = reference_counts.get(slot, 0)
            reference_counts[slot] = index + 1
            records.append(
                {
                    "owner_xml_id": owner,
                    "language_index": language,
                    "reference_index": index,
                    "kind": tag,
                    "target_xml_id": node["attributes"]["ref"],
                }
            )
        for child in node.get("children", []):
            visit(child, owner, language)

    visit(tree)
    return records


def assert_original_occurrences(actual, expected):
    assert actual == [
        {
            "owner_xml_id": item["owner_xml_id"],
            "language_index": item["language_index"],
            "reference_index": item["reference_index"],
            "kind": item["reference"]["kind"],
            "target_xml_id": item["reference"]["target_xml_id"],
        }
        for item in expected
    ]


def assert_owned_paragraph_blocks(blocks, expected, yj):
    references = [item["references"] for item in expected["items"]] + [[]]
    assert blocks == [
        {
            "kind": "paragraph",
            "text": text,
            "context": {"product_yj_codes": [yj], "labels": []},
            "references": refs,
        }
        for text, refs in zip(expected["body"], references, strict=True)
    ]


def test_tc121_x16_7_all_ten_item_contexts_and_25_original_positions(
    registered_publisher,
):
    document = ORACLE[0]
    expected = document["sections"]["16.7"]
    directory = registered_publisher.store._target(
        DocumentId(document["document_id"]), document["sha256"]
    )
    original = next(
        (ROOT / "data/pmda/originals").glob(f"*/{document['document_id']}.xml")
    )
    assert (directory / "source.xml").read_bytes() == original.read_bytes()
    stored = json.loads((directory / "document.json").read_bytes())
    tree = next(
        section["tree"] for section in stored["sections"] if section["code"] == "16.7"
    )
    positions = stored_reference_positions(tree)
    assert_original_occurrences(positions, expected["raw_reference_occurrences"])
    with closing(
        sqlite3.connect(registered_publisher.index_path.as_uri() + "?mode=ro", uri=True)
    ) as connection:
        payload = json.loads(
            connection.execute(
                "SELECT payload_json FROM units WHERE unit_id=?", (expected["unit_id"],)
            ).fetchone()[0]
        )
    assert_owned_paragraph_blocks(payload["blocks"], expected, document["yj"])
    assert payload["references"] == expected["references"]
    changed = copy.deepcopy(positions)
    changed[3]["owner_xml_id"] = "HDR_DrugAndDrugInteractions_3"
    with pytest.raises(AssertionError):
        assert_original_occurrences(changed, expected["raw_reference_occurrences"])
    changed = copy.deepcopy(payload["blocks"])
    changed[1]["references"], changed[2]["references"] = (
        changed[2]["references"],
        changed[1]["references"],
    )
    with pytest.raises(AssertionError):
        assert_owned_paragraph_blocks(changed, expected, document["yj"])
    with pytest.raises(AssertionError):
        assert_owned_paragraph_blocks(payload["blocks"][-1:], expected, document["yj"])


@pytest.mark.asyncio
@pytest.mark.parametrize("pair", [True, False])
@pytest.mark.parametrize(
    "profile", ["jev_first", "keyword_first", "unavailable", "empty_keyword"]
)
@pytest.mark.parametrize("reverse", [False, True])
async def test_tc120_122_all_detector_collection_and_tc121_original_tables(
    registered_publisher, pair, profile, reverse
):
    finished = []

    class Classifier:
        async def classify(self, request):
            await asyncio.sleep(0.03 if profile == "keyword_first" else 0)
            finished.append("jev")
            return IntentResult(
                is_available=profile != "unavailable",
                candidates=(
                    IntentCandidate(IntentName("interaction"), Probability(1.0)),
                ),
            )

    class Keywords:
        def extract_keywords(self, text):
            time.sleep(0.03 if profile == "jev_first" else 0)
            finished.append("keyword")
            return () if profile == "empty_keyword" else ("158",)

    workers = ReadWorkers()
    runtime = GenerationRuntime(registered_publisher, workers=workers)
    message = "イグザレルト錠2.5mgの飲み合わせ"
    if pair:
        message = (
            "イトラコナゾールとイグザレルト錠2.5mgの飲み合わせを教えて"
            if reverse
            else "イグザレルト錠2.5mgとイトラコナゾールの飲み合わせを教えて"
        )
    try:
        async with runtime.acquire() as snapshot:
            conditions = []

            class RecordingReader:
                async def search(self, criteria, medicines):
                    conditions.append(
                        {
                            "source": criteria.source.value,
                            "intent": criteria.intent.value
                            if criteria.intent
                            else None,
                            "section_codes": [
                                code.value for code in criteria.section_codes
                            ],
                            "keywords": [word.value for word in criteria.keywords],
                            "target_yj_codes": sorted(
                                code
                                for medicine in medicines
                                for code in medicine.yj_codes
                            ),
                        }
                    )
                    return await snapshot.evidence_reader.search(criteria, medicines)

            result = await retrieve_evidence(
                message,
                [item[2] for item in DOCUMENTS] if pair else [DOCUMENTS[0][2]],
                medicine_reader=snapshot.medicine_reader,
                evidence_reader=RecordingReader(),
                intent_classifier=Classifier(),
                keyword_extractor=Keywords(),
                intent_policy=get_package_insert_definitions().intent_policy,
            )
        expected_docs = ORACLE if pair else ORACLE[:1]
        expected = sorted(
            [
                (doc["sections"][code]["unit_id"], doc, code)
                for doc in expected_docs
                for code in doc["sections"]
            ],
            key=lambda item: (tuple(int(part) for part in item[2].split(".")), item[0]),
        )
        assert [source.unit_id.value for source in result.sources] == [
            item[0] for item in expected
        ]
        assert not result.needs_clarification
        assert {yj for med in result.resolved_medicines for yj in med.yj_codes} == {
            doc["yj"] for doc in expected_docs
        }
        target_codes = sorted(doc["yj"] for doc in expected_docs)
        expected_conditions = [
            {
                "source": "logic",
                "intent": "interaction",
                "section_codes": ["10", "10.1", "10.2", "16.7"],
                "keywords": [],
                "target_yj_codes": target_codes,
            }
        ]
        if profile != "unavailable":
            expected_conditions.append(
                {
                    "source": "jev",
                    "intent": "interaction",
                    "section_codes": ["10", "10.1", "10.2", "16.7"],
                    "keywords": [],
                    "target_yj_codes": target_codes,
                }
            )
        if profile != "empty_keyword":
            expected_conditions.append(
                {
                    "source": "keyword",
                    "intent": None,
                    "section_codes": [],
                    "keywords": ["158"],
                    "target_yj_codes": target_codes,
                }
            )
        assert sorted(conditions, key=lambda item: item["source"]) == sorted(
            expected_conditions, key=lambda item: item["source"]
        )
        for source, (_, document, code) in zip(result.sources, expected, strict=True):
            assert_source(source, document, code)
            by = {"logic"}
            if profile != "unavailable":
                by.add("jev")
            if (
                pair
                and document is not ORACLE[0]
                and code == "10.1"
                and profile != "empty_keyword"
            ):
                by.add("keyword")
            assert {item.value for item in source.retrieved_by} == by
        if profile == "jev_first":
            assert finished == ["jev", "keyword"]
        elif profile == "keyword_first":
            assert finished == ["keyword", "jev"]
    finally:
        await workers.aclose()


@pytest.mark.asyncio
async def test_tc121_complete_six_tables_and_original_reference_destinations(
    registered_publisher,
):
    workers = ReadWorkers()
    runtime = GenerationRuntime(registered_publisher, workers=workers)
    try:
        async with runtime.acquire() as snapshot:
            catalog = AttachmentProductCatalog(
                await snapshot.medicine_reader.read_medicines()
            )
            selected = tuple(
                catalog.resolve_medicines("", [doc[2] for doc in DOCUMENTS])
            )
            sources = await snapshot.evidence_reader.search(
                SearchCriteria(
                    source=DetectionSource.LOGIC,
                    section_codes=(
                        SearchSectionCode("10.1"),
                        SearchSectionCode("10.2"),
                    ),
                ),
                selected,
            )
        sources = sorted(sources, key=lambda source: source.unit_id.value)
        expected = sorted(
            [
                (doc["sections"][code]["unit_id"], doc, code)
                for doc in ORACLE
                for code in ("10.1", "10.2")
            ],
            key=lambda item: item[0],
        )
        assert [source.unit_id.value for source in sources] == [
            item[0] for item in expected
        ]
        for source, (_, doc, code) in zip(sources, expected, strict=True):
            assert_source(source, doc, code)
    finally:
        await workers.aclose()


def assert_prompt_oracle(messages, documents, *, history=True):
    question = (
        "イグザレルト錠2.5mgとイトラコナゾールの飲み合わせを教えて"
        if len(documents) == 3
        else "イグザレルト錠2.5mgの飲み合わせ"
    )
    expected_conversation = (
        [{"role": "assistant", "content": "前の回答を保持"}] if history else []
    )
    expected_conversation.append({"role": "user", "content": question})
    assert messages[1:] == expected_conversation
    blocks = messages[0]["content"].split("[根拠 ")[1:]
    expected = sorted(
        [
            (doc["sections"][code]["unit_id"], doc, code)
            for doc in documents
            for code in doc["sections"]
        ],
        key=lambda item: (tuple(int(part) for part in item[2].split(".")), item[0]),
    )
    assert len(blocks) == len(expected)
    for number, (block, (unit_id, doc, code)) in enumerate(
        zip(blocks, expected, strict=True), 1
    ):
        assert block.startswith(f"{number}] (単位ID: {unit_id})\n")
        assert f"- 対象製品: {doc['product_name']}\n" in block
        assert f"- YJコード: {doc['yj']}\n" in block
        revision = doc["revision"]
        assert (
            f"- 改訂情報: 今回 / {revision['year_month']} / {revision['version']}\n"
            in block
        )
        assert (
            f"- 出典URL: https://www.pmda.go.jp/PmdaSearch/iyakuDetail/{doc['document_id']}\n"
            in block
        )
        title = {
            "10": "相互作用",
            "10.1": "併用禁忌",
            "10.2": "併用注意",
            "16.7": "薬物相互作用",
        }[code]
        assert f"- 項目: {code} {title}\n" in block
        parser = Cells()
        parser.feed(block)
        assert parser.rows == doc["sections"][code]["rows"]
        assert parser.paragraphs == doc["sections"][code]["body"]
        for ref in doc["sections"][code]["references"]:
            assert (
                f"{ref['kind']}: 項目 {ref['target_section_code']} {ref['target_url']}"
                in block
            )


@pytest.mark.asyncio
@pytest.mark.parametrize("pair", [False, True])
async def test_tc123_all_evidence_reaches_recording_provider_and_conversation(
    registered_publisher, pair
):
    class Classifier:
        async def classify(self, request):
            return IntentResult(
                is_available=True,
                candidates=(
                    IntentCandidate(IntentName("interaction"), Probability(1.0)),
                ),
            )

    class Keywords:
        def extract_keywords(self, text):
            return ("158",)

    class Provider:
        def __init__(self):
            self.messages = []

        async def stream_response(self, messages, model=None):
            self.messages = copy.deepcopy(messages)
            yield "送信観測のみ"

    workers = ReadWorkers()
    runtime = GenerationRuntime(registered_publisher, workers=workers)
    provider = Provider()
    question = (
        "イグザレルト錠2.5mgとイトラコナゾールの飲み合わせを教えて"
        if pair
        else "イグザレルト錠2.5mgの飲み合わせ"
    )
    conversation = [
        ChatMessage("system", "古いsystemは送らない"),
        ChatMessage("assistant", "前の回答を保持"),
        ChatMessage("user", question),
    ]
    try:
        async with runtime.acquire() as snapshot:
            reply = await answer_question(
                conversation,
                [doc[2] for doc in DOCUMENTS] if pair else [DOCUMENTS[0][2]],
                medicine_reader=snapshot.medicine_reader,
                evidence_reader=snapshot.evidence_reader,
                intent_classifier=Classifier(),
                keyword_extractor=Keywords(),
                intent_policy=get_package_insert_definitions().intent_policy,
                answer_prompt_policy=get_package_insert_definitions().answer_prompt_policy,
                provider_factory=lambda _: provider,
                provider_name=None,
                model_name=None,
            )
        assert reply.answer == "送信観測のみ"
        documents = ORACLE if pair else ORACLE[:1]
        assert_prompt_oracle(provider.messages, documents)
        altered = copy.deepcopy(provider.messages)
        altered[0]["content"] = altered[0]["content"].replace(
            documents[0]["sections"]["10"]["unit_id"], "欠落", 1
        )
        with pytest.raises(AssertionError):
            assert_prompt_oracle(altered, documents)
        prefix, final_block = provider.messages[0]["content"].rsplit("[根拠 ", 1)
        altered = copy.deepcopy(provider.messages)
        altered[0]["content"] = (
            prefix + "[根拠 " + final_block.replace("リトナビル", "本文欠落")
        )
        with pytest.raises(AssertionError):
            assert_prompt_oracle(altered, documents)
        altered = copy.deepcopy(provider.messages)
        missing_url = ORACLE[0]["sections"]["16.7"]["references"][0]["target_url"]
        altered[0]["content"] = (
            prefix + "[根拠 " + final_block.replace(missing_url, "参照欠落")
        )
        with pytest.raises(AssertionError):
            assert_prompt_oracle(altered, documents)
    finally:
        await workers.aclose()
