"""TC132/135: copy実SQLite lease、所有child publisher、固定SDKdouble。"""

import asyncio
import hashlib
import sqlite3
import subprocess
import sys
from contextlib import asynccontextmanager, closing
from typing import TypedDict

import pytest
from backend.application.chat.answer_preparation import prepare_reply
from backend.application.chat.answer_question import answer_question
from backend.application.chat.chat_models import ChatMessage
from backend.application.chat.stream_reply import stream_reply
from backend.application.medicine.product_models import RegisteredMedicine
from backend.application.retrieval.intent_contracts import IntentRequest, IntentResult
from backend.application.retrieval.retrieve_evidence import retrieve_evidence
from backend.application.retrieval.snapshot_contracts import RetrievalSnapshot
from backend.domain.retrieval.value_objects import IntentPolicy
from backend.infrastructure.package_insert_definitions.loader import (
    get_package_insert_definitions,
)
from backend.infrastructure.persistence.generation_runtime import GenerationRuntime
from backend.infrastructure.persistence.read_workers import ReadWorkers
from backend.tests.application.retrieval.test_product_identity_retrieval import (
    Classifier,
    Keywords,
)
from backend.tests.integration.test_registration_publisher import publish, source
from backend.tests.integration.test_registration_publisher import publisher as publisher

X = "111111111111"
A = "222222222222"
ITRA = "333333333333"


def named(body, name, code, doc, *, revised_at="2026-10"):
    return source(body, (code,), doc=doc, revised_at=revised_at).replace(
        "製品A".encode(), name.encode()
    )


def leases(publisher):
    with closing(
        sqlite3.connect(f"{publisher.index_path.as_uri()}?mode=ro", uri=True)
    ) as c:
        return c.execute("SELECT count(*) FROM generation_leases").fetchone()[0]


class ForbiddenSearch:
    async def read_medicines(self) -> tuple[RegisteredMedicine, ...]:
        raise AssertionError("snapshot must supply its real medicine reader")

    def __init__(self):
        self.calls = 0

    async def search(self, criteria, medicines):
        self.calls += 1
        raise AssertionError("early stop cannot search")


class CountingProvider:
    def __init__(self):
        self.factory_calls = 0
        self.stream_calls = 0

    def factory(self, name):
        self.factory_calls += 1
        raise AssertionError("clarification cannot create generation provider")

    async def stream_response(self, messages, model=None):
        self.stream_calls += 1
        raise AssertionError("clarification cannot generate")
        yield "unreachable"


class ObservedRuntime:
    def __init__(self, runtime, reader):
        self.runtime = runtime
        self.reader = reader
        self.generations = []

    @asynccontextmanager
    async def acquire(self):
        async with self.runtime.acquire() as snapshot:
            self.generations.append(snapshot.generation_id)
            yield RetrievalSnapshot(
                snapshot.generation_id, snapshot.medicine_reader, self.reader
            )


class Dependencies(TypedDict):
    medicine_reader: ForbiddenSearch
    evidence_reader: ForbiddenSearch
    intent_classifier: Classifier
    keyword_extractor: Keywords
    intent_policy: IntentPolicy
    snapshot_provider: ObservedRuntime


@pytest.mark.asyncio
@pytest.mark.parametrize("entry", ["prepare", "answer", "stream"])
@pytest.mark.parametrize(
    "message,codes,strategy",
    [
        ("アマリールの効能", [X], "product_identity_conflict"),
        ("イグザレルトとイトラコナゾールの飲み合わせ", [X], "pair_yj_codes_required"),
        ("イグザレルトと未知薬の併用", [X], "unresolved_counterpart"),
        ("アマリールの効能", [X, "999999999999"], "product_identity_conflict"),
        ("アマリールの効能", ["999999999999"], "product_code_lookup"),
    ],
)
async def test_tc132_all_early_entries_release_real_lease_without_search_generation(
    publisher, entry, message, codes, strategy
):
    publish(publisher, named("原文X", "イグザレルト", X, "x"))
    publish(publisher, named("原文A", "アマリール", A, "a"))
    final = publish(publisher, named("原文I", "イトラコナゾール", ITRA, "i"))
    workers = ReadWorkers()
    runtime = GenerationRuntime(publisher, workers=workers)
    search = ForbiddenSearch()
    observed = ObservedRuntime(runtime, search)
    provider = CountingProvider()
    conversation = [ChatMessage("user", message)]
    kwargs: Dependencies = {
        "medicine_reader": search,
        "evidence_reader": search,
        "intent_classifier": Classifier(),
        "keyword_extractor": Keywords(),
        "intent_policy": get_package_insert_definitions().intent_policy,
        "snapshot_provider": observed,
    }

    try:
        if entry == "answer":
            reply = await answer_question(
                conversation,
                codes,
                **kwargs,
                answer_prompt_policy=get_package_insert_definitions().answer_prompt_policy,
                provider_factory=provider.factory,
                provider_name=None,
                model_name=None,
            )
        else:
            reply = await prepare_reply(conversation, codes, **kwargs)
            if entry == "stream":
                chunks = [
                    chunk
                    async for chunk in stream_reply(
                        reply,
                        conversation,
                        answer_prompt_policy=get_package_insert_definitions().answer_prompt_policy,
                        provider_factory=provider.factory,
                        provider_name=None,
                        model_name=None,
                    )
                ]
                assert chunks == [reply.answer]
        assert (
            reply.retrieval_strategy == strategy
            and reply.needs_clarification
            and reply.sources == []
        )
        expected_codes = [] if strategy == "product_code_lookup" else [X]
        assert [
            code for m in reply.resolved_medicines for code in m.yj_codes
        ] == expected_codes
        assert observed.generations[0].value == final.generation_id
        assert search.calls == provider.factory_calls == provider.stream_calls == 0
        assert leases(publisher) == 0
    finally:
        await workers.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["exception", "cancel"])
async def test_tc132_classifier_exception_cancel_release_real_lease(publisher, failure):
    publish(publisher, named("原文X", "イグザレルト", X, "x"))
    workers = ReadWorkers()
    runtime = GenerationRuntime(publisher, workers=workers)
    entered = asyncio.Event()

    class BlockingClassifier:
        async def classify(self, request: IntentRequest) -> IntentResult:
            entered.set()
            if failure == "exception":
                raise RuntimeError("controlled detector failure")
            await asyncio.Event().wait()
            raise AssertionError("cancel test must never resume classifier")

    task = asyncio.create_task(
        retrieve_evidence(
            "アマリールの効能",
            [X],
            medicine_reader=ForbiddenSearch(),
            evidence_reader=ForbiddenSearch(),
            intent_classifier=BlockingClassifier(),
            keyword_extractor=Keywords(),
            intent_policy=get_package_insert_definitions().intent_policy,
            snapshot_provider=runtime,
        )
    )
    try:
        await entered.wait()
        if failure == "cancel":
            assert leases(publisher) == 1
            task.cancel()
        with pytest.raises(
            RuntimeError if failure == "exception" else asyncio.CancelledError
        ):
            await task
        assert leases(publisher) == 0
    finally:
        await workers.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("confirmation", [False, True])
async def test_tc135_identity_and_materialize_stay_old_across_os_publish(
    publisher, tmp_path, confirmation, monkeypatch
):
    old = named("旧原文X", "イグザレルト", X, "x")
    publish(publisher, old)
    first = publish(publisher, named("旧原文A", "アマリール", A, "a"))
    workers = ReadWorkers()
    runtime = GenerationRuntime(publisher, workers=workers)
    entered = asyncio.Event()
    release = asyncio.Event()

    from backend.application.medicine.product_catalog import MedicineCatalog

    resolved_before_barrier = []
    original_resolve = MedicineCatalog.resolve_medicines

    def observed_resolve(self, message, codes):
        result = original_resolve(self, message, codes)
        resolved_before_barrier.append(result)
        return result

    monkeypatch.setattr(MedicineCatalog, "resolve_medicines", observed_resolve)

    class PausedClassifier(Classifier):
        async def classify(self, request):
            entered.set()
            await release.wait()
            return await super().classify(request)

    class BodyKeywords:
        def extract_keywords(self, text):
            return ("原文",)

    message = "アマリールの効能" if confirmation else "イグザレルトの副作用"

    async def retrieve(classifier):
        return await retrieve_evidence(
            message,
            [X],
            medicine_reader=ForbiddenSearch(),
            evidence_reader=ForbiddenSearch(),
            intent_classifier=classifier,
            keyword_extractor=BodyKeywords(),
            intent_policy=get_package_insert_definitions().intent_policy,
            snapshot_provider=runtime,
        )

    task = asyncio.create_task(retrieve(PausedClassifier()))
    try:
        await entered.wait()
        assert leases(publisher) == 1
        assert resolved_before_barrier, (
            "selected resolution must precede publication barrier"
        )
        assert resolved_before_barrier[0][0].brand_names == ("イグザレルト",)
        paths = []
        for name, value in [
            ("x", named("新原文X", "新製品X", X, "x", revised_at="2026-11")),
            ("a", named("新原文A", "別製品Z", A, "a", revised_at="2026-11")),
        ]:
            path = tmp_path / f"replacement-{name}.xml"
            path.write_bytes(value)
            paths.append(path)
        script = "from pathlib import Path;import sys;from backend.infrastructure.persistence.registration_publisher import SqliteRegistrationPublisher;from backend.infrastructure.persistence.attachment_import_store import FileAttachmentImportStore;from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder;p=SqliteRegistrationPublisher(Path(sys.argv[1]),FileAttachmentImportStore(Path(sys.argv[2])));[(p.publish(PmdaXmlDecoder().decode(v:=Path(f).read_bytes()),v)) for f in sys.argv[3:]]"
        result = await asyncio.to_thread(
            subprocess.run,
            [
                sys.executable,
                "-c",
                script,
                str(publisher.index_path),
                str(publisher.store.root),
                *[str(x) for x in paths],
            ],
            capture_output=True,
            timeout=60,
        )
        assert result.returncode == 0, result.stderr.decode(errors="replace")
        assert leases(publisher) == 1
        release.set()
        previous = await task
        assert previous.resolved_medicines[0].brand_names == ("イグザレルト",)
        assert previous.retrieval_strategy == (
            "product_identity_conflict" if confirmation else "three_detectors"
        )
        if confirmation:
            assert previous.sources == []
        else:
            assert [s.unit_id.value for s in previous.sources] == [
                f"000001_x:{hashlib.sha256(old).hexdigest()}:1"
            ]
            assert (
                "旧原文X" in previous.sources[0].excerpt
                and "新原文X" not in previous.sources[0].excerpt
            )
        assert leases(publisher) == 0
        current = await retrieve(Classifier())
        assert current.retrieval_strategy == "three_detectors"
        assert current.resolved_medicines[0].brand_names == ("新製品X",)
        assert len(current.sources) == 1 and "新原文X" in current.sources[0].excerpt
        assert (
            leases(publisher) == 0
            and runtime.cached_generation_id != first.generation_id
        )
    finally:
        release.set()
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        await workers.aclose()


@pytest.mark.asyncio
async def test_tc130_correct_amaryl_original_indication_reaches_generation(publisher):
    from backend.application.retrieval.intent_contracts import IntentResult
    from backend.domain.retrieval.primitives import IntentName, Probability
    from backend.domain.retrieval.value_objects import IntentCandidate
    from backend.tests.support.interaction_raw_oracle import ROOT

    raw = next(
        (ROOT / "data/pmda/originals").glob("*/780069_3961008F1020_1_30.xml")
    ).read_bytes()
    publish(publisher, raw)

    class EfficacyClassifier:
        async def classify(self, request):
            return IntentResult(
                True, {}, (IntentCandidate(IntentName("efficacy"), Probability(1.0)),)
            )

    class Provider:
        def __init__(self):
            self.factory_calls = 0
            self.stream_calls = 0
            self.messages = []

        def factory(self, name):
            self.factory_calls += 1
            return self

        async def stream_response(self, messages, model=None):
            self.stream_calls += 1
            self.messages = messages
            yield "正常生成"

    workers = ReadWorkers()
    runtime = GenerationRuntime(publisher, workers=workers)
    provider = Provider()
    try:
        reply = await answer_question(
            [ChatMessage("user", "アマリールの効能は？")],
            ["3961008F1020"],
            medicine_reader=ForbiddenSearch(),
            evidence_reader=ForbiddenSearch(),
            intent_classifier=EfficacyClassifier(),
            keyword_extractor=Keywords(),
            intent_policy=get_package_insert_definitions().intent_policy,
            answer_prompt_policy=get_package_insert_definitions().answer_prompt_policy,
            provider_factory=provider.factory,
            provider_name=None,
            model_name=None,
            snapshot_provider=runtime,
        )
        assert (
            reply.retrieval_strategy == "three_detectors"
            and not reply.needs_clarification
        )
        assert [s.unit_id.value for s in reply.sources] == [
            f"780069_3961008F1020_1_30:{hashlib.sha256(raw).hexdigest()}:4"
        ]
        assert "糖尿病" in reply.sources[0].excerpt
        assert "糖尿病" in str(provider.messages) and "4 効能又は効果" in str(
            provider.messages
        )
        assert reply.resolved_medicines[0].yj_codes == ("3961008F1020",)
        assert (
            provider.factory_calls == provider.stream_calls == 1
            and reply.answer == "正常生成"
        )
        assert leases(publisher) == 0
    finally:
        await workers.aclose()
