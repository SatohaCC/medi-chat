"""TC124–131: real catalog + retrieval、外部検出器は決定的double。"""

from dataclasses import asdict

import pytest
from backend.application.medicine.product_models import RegisteredMedicine
from backend.application.retrieval.intent_contracts import IntentResult
from backend.application.retrieval.retrieve_evidence import retrieve_evidence
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.attachment.primitives import PmdaUrl
from backend.domain.attachment.value_objects import (
    AttachmentProductRevision,
    MedicineDocumentReference,
)
from backend.domain.medicine.entities import MedicineProduct
from backend.domain.medicine.identifiers import YjCode
from backend.domain.retrieval.primitives import IntentName, Probability
from backend.domain.retrieval.value_objects import IntentCandidate
from backend.infrastructure.package_insert_definitions.loader import (
    get_package_insert_definitions,
)
from backend.tests.test_evidence_collection import make_evidence

X = "3339003F5020"
ITRA = "6290004M1029"
J = "6290004M1070"
A = "3961008F1022"
RECORDS = tuple(
    RegisteredMedicine(
        medicine=MedicineProduct(
            yj_code=YjCode(code),
            brand_name=brand,
            generic_name=generic,
            english_name="",
            hiragana_name="",
        ),
        reference=MedicineDocumentReference(
            document_id=DocumentId(doc),
            pmda_url=PmdaUrl("https://example.test"),
            revision=AttachmentProductRevision({}),
        ),
    )
    for doc, code, brand, generic in [
        ("x", X, "イグザレルト錠2.5mg", "リバーロキサバン"),
        ("i", ITRA, "イトリゾールカプセル50", "イトラコナゾール"),
        ("j", J, "イトラコナゾールカプセル50mg「SW」", "イトラコナゾール"),
        ("a", A, "アマリール錠1mg", "グリメピリド"),
    ]
)


class Medicines:
    async def read_medicines(self):
        return RECORDS


class Classifier:
    is_available = True

    async def classify(self, request):
        return IntentResult(
            True,
            {"fixed": True},
            (IntentCandidate(IntentName("interaction"), Probability(1.0)),),
        )


class Keywords:
    def extract_keywords(self, text):
        return ()


class EvidenceReader:
    def __init__(self, forbidden):
        self.calls = []
        self.forbidden = forbidden

    async def search(self, criteria, medicines):
        self.calls.append((criteria, medicines))
        assert not self.forbidden, "clarification must not search"
        return (make_evidence(),)


@pytest.mark.asyncio
@pytest.mark.parametrize("progressive", [False, True])
@pytest.mark.parametrize(
    "message,codes,strategy",
    [
        ("アマリールの効能は？", [X], "product_identity_conflict"),
        ("イグザレルトとイトラコナゾールの飲み合わせ", [X], "pair_yj_codes_required"),
        ("イグザレルトと未知薬の併用は可能ですか", [X], "unresolved_counterpart"),
    ],
)
async def test_tc124_126_real_catalog_early_stop(message, codes, strategy, progressive):
    async def publish(sources):
        raise AssertionError("clarification must not publish partial evidence")

    reader = EvidenceReader(True)
    result = await retrieve_evidence(
        message,
        codes,
        medicine_reader=Medicines(),
        evidence_reader=reader,
        intent_classifier=Classifier(),
        keyword_extractor=Keywords(),
        intent_policy=get_package_insert_definitions().intent_policy,
        on_logic_sources=publish if progressive else None,
    )
    assert result.retrieval_strategy == strategy
    assert result.needs_clarification and result.sources == [] and reader.calls == []
    assert [
        {**asdict(m.medicine), "document_ids": m.document_ids}
        for m in result.resolved_medicines
    ] == [
        {
            "generic_name": "リバーロキサバン",
            "brand_names": ("イグザレルト錠2.5mg",),
            "yj_codes": (X,),
            "document_ids": ("x",),
            "matched_aliases": (),
        }
    ]
    assert result.intent == "interaction" and result.jev_response == {"fixed": True}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message,codes,expected,strategy",
    [
        (
            "アマリールの効能。イグザレルトと未知薬の併用",
            [X, "999999999999"],
            [X],
            "product_code_lookup",
        ),
        (
            "アマリールの効能。イグザレルトと未知薬の併用",
            [X],
            [X],
            "product_identity_conflict",
        ),
        (
            "イグザレルトとイトラコナゾールの併用。イグザレルトと未知薬の併用",
            [X],
            [X],
            "unresolved_counterpart",
        ),
        (
            "イグザレルトとイトラコナゾールの併用",
            [X, ITRA],
            [X, ITRA],
            "three_detectors",
        ),
        ("イグザレルトとイトラコナゾールの併用", [X, J], [X, J], "three_detectors"),
        ("イグザレルトとイトリゾールの併用", [X, J], [X, J], "pair_yj_codes_required"),
        ("イトラコナゾールの効能", [ITRA], [ITRA], "three_detectors"),
        ("アマリールの効能", [A], [A], "three_detectors"),
        ("この薬の副作用", [X], [X], "three_detectors"),
        ("イグザレルトの飲み合わせ", [X], [X], "three_detectors"),
        ("『アマリールの効能』", [X], [X], "three_detectors"),
        (
            "記録：アマリールの効能。イグザレルトの副作用を教えて",
            [X],
            [X],
            "three_detectors",
        ),
        ("未知単剤の効能", [X], [X], "three_detectors"),
        ("一般文中アマリールの効能", [X], [X], "three_detectors"),
        ("イトラコナゾールカプセル50mg「SW」の効能", [J], [J], "three_detectors"),
        (
            "イトラコナゾールカプセル50mg「SW」の効能",
            [ITRA],
            [ITRA],
            "product_identity_conflict",
        ),
        (
            "イグザレルトとイトラコナゾールの併用",
            [X, A],
            [X, A],
            "pair_yj_codes_required",
        ),
    ],
)
async def test_tc128_131_priority_alternatives_normal_selected_only(
    message, codes, expected, strategy
):
    reader = EvidenceReader(strategy != "three_detectors")
    result = await retrieve_evidence(
        message,
        codes,
        medicine_reader=Medicines(),
        evidence_reader=reader,
        intent_classifier=Classifier(),
        keyword_extractor=Keywords(),
        intent_policy=get_package_insert_definitions().intent_policy,
    )
    assert result.retrieval_strategy == strategy
    assert [code for m in result.resolved_medicines for code in m.yj_codes] == expected
    records = {r.yj_code.value: r for r in RECORDS if r.yj_code}
    for m in result.resolved_medicines:
        assert m.brand_names == tuple(records[c].brand_name for c in m.yj_codes)
        assert m.document_ids == tuple(records[c].document_id.value for c in m.yj_codes)
        assert m.matched_aliases == ()
    assert bool(reader.calls) == (strategy == "three_detectors")
    assert bool(result.sources) == (strategy == "three_detectors")
    assert result.needs_clarification == (strategy != "three_detectors")
