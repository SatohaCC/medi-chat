"""PG-028～032: public snapshot semantics and independent XML/search oracles."""

import hashlib
import json

import pytest
from backend.application.indexing.values import SearchSectionCode
from backend.application.retrieval.queries.dtos.evidence import evidence_payload
from backend.application.retrieval.queries.models import SearchCriteria
from backend.application.retrieval.values import DetectionSource, SearchKeyword
from backend.domain.medicine.identifiers import YjCode
from backend.domain.medicine.primitives import BrandName, MatchedAlias
from backend.infrastructure.persistence.queries.postgres_search_snapshot_provider import (
    PostgresRuntime,
)
from backend.infrastructure.persistence.runtime.read_workers import ReadWorkers
from backend.tests.application.indexing.test_active_attachment_projection import (
    mixed_source,
)
from backend.tests.integration.test_postgres_registration import (
    pg_publisher as pg_publisher,
)
from backend.tests.integration.test_postgres_registration import publish
from backend.tests.integration.test_postgres_snapshot import target, warning_criteria
from backend.tests.support.attachment_import_fixtures import xml_source
from backend.tests.support.paths import FIXTURES_ROOT
from backend.tests.support.postgres_fixtures import pg_engines as pg_engines
from backend.tests.support.registration_oracles import source

ORACLE = json.loads(
    (FIXTURES_ROOT / "postgres_public_snapshot_oracle.json").read_text(encoding="utf-8")
)


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["medicine", "search"])
async def test_pg028_public_corpus_and_equal_rank_use_legacy_codepoint_order(
    pg_engines, pg_publisher, operation
):
    from backend.application.medicine.queries.models import ResolvedMedicine
    from backend.domain.medicine.value_objects import MedicineMatch

    codes = tuple(f"11111111111{index}" for index in range(5))
    for name, code in zip(("a", "B", "亜", "A", "b"), codes, strict=True):
        publish(pg_publisher, source("テスト同順位", (code,), doc=name))
    workers = ReadWorkers()
    try:
        async with PostgresRuntime(
            pg_engines[1], workers=workers
        ).acquire() as snapshot:
            if operation == "medicine":
                rows = await snapshot.medicine_reader.read_medicines()
            else:
                rows = await snapshot.evidence_reader.search(
                    SearchCriteria(
                        source=DetectionSource.KEYWORD,
                        keywords=(SearchKeyword("テスト同順位"),),
                    ),
                    (
                        ResolvedMedicine(
                            medicine=MedicineMatch(
                                generic_name=None,
                                brand_names=tuple(BrandName(value) for value in ()),
                                yj_codes=tuple(YjCode(value) for value in codes),
                                matched_aliases=tuple(
                                    MatchedAlias(value) for value in ()
                                ),
                            ),
                            document_ids=(
                                "000001_a",
                                "000001_B",
                                "000001_亜",
                                "000001_A",
                                "000001_b",
                            ),
                        ),
                    ),
                )
            assert [row.document_id.value for row in rows] == [
                "000001_A",
                "000001_B",
                "000001_a",
                "000001_b",
                "000001_亜",
            ]
    finally:
        await workers.aclose()


def oracle_source():
    blocks = tuple(
        zip(
            (
                "Warnings",
                "ContraIndications",
                "ImportantPrecautions",
                "OtherPrecautions",
                "PrecautionsForApplication",
            ),
            (
                "注意事項",
                "注意事項注意事項注意事項",
                "注意事項 ＡＢＣ１２３ café Cafe\u0301 under_score 東京 大阪",
                "注意事項。" + "関係のない長い説明です。" * 10,
                "別の記載",
            ),
            strict=True,
        )
    )
    return xml_source(
        "".join(
            f"<{tag}><Detail><Lang>{body}</Lang></Detail></{tag}>"
            for tag, body in blocks
        )
    ).replace(
        b"</PackIns>",
        "<GenericName><Lang>テスト一般名</Lang></GenericName></PackIns>".encode(),
    )


@pytest.mark.asyncio
async def test_pg028_030_snapshot_retains_ids_order_payload(pg_engines, pg_publisher):
    raw = oracle_source()
    assert hashlib.sha256(raw).hexdigest() == ORACLE["source_sha256"]
    for value in (
        raw,
        source("別薬の注意事項注意事項", ("222222222222",), doc="other"),
    ):
        publish(pg_publisher, value)
    workers = ReadWorkers()
    try:
        async with PostgresRuntime(pg_engines[1], workers=workers).acquire() as scope:
            products = await scope.medicine_reader.read_medicines()
            assert [
                {
                    "yj_code": item.yj_code.value if item.yj_code else None,
                    "brand_name": item.brand_name,
                    "generic_name": item.generic_name,
                    "english_name": item.english_name,
                    "pmda_url": item.pmda_url.value if item.pmda_url else None,
                    "revision": item.revision.to_dict(),
                }
                for item in products
            ] == ORACLE["medicines"]
            for case in ORACLE["criteria"]:
                criteria = SearchCriteria(
                    source=DetectionSource(case["source"]),
                    section_codes=tuple(
                        SearchSectionCode(code) for code in case["sections"]
                    ),
                    keywords=tuple(
                        SearchKeyword(keyword) for keyword in case["keywords"]
                    ),
                )
                actual = await scope.evidence_reader.search(criteria, target())
                assert [evidence_payload(item) for item in actual] == case[
                    "expected"
                ], case
    finally:
        await workers.aclose()


@pytest.mark.asyncio
async def test_pg031_more_than_four_hundred_results_have_no_limit(
    pg_engines, pg_publisher
):
    from backend.application.medicine.queries.models import ResolvedMedicine
    from backend.domain.medicine.value_objects import MedicineMatch
    from backend.infrastructure.persistence.registration.registration_payloads import (
        PostgresRegistrationInput,
    )
    from backend.infrastructure.pmda_xml.pmda_xml_decoder import PmdaXmlDecoder

    codes = tuple(f"{number:012d}" for number in range(1, 451))
    originals = tuple(
        source("テスト全件検索", (code,), doc=f"test{number:03d}")
        for number, code in enumerate(codes)
    )
    receipts = pg_publisher.publish_inputs(
        tuple(
            PostgresRegistrationInput(PmdaXmlDecoder().decode(raw), raw)
            for raw in originals
        ),
        initial=True,
    )
    medicines = (
        ResolvedMedicine(
            MedicineMatch(
                generic_name=None,
                brand_names=tuple(BrandName(value) for value in ()),
                yj_codes=tuple(YjCode(value) for value in codes),
                matched_aliases=tuple(MatchedAlias(value) for value in ()),
            ),
            tuple(receipt.document_id for receipt in receipts),
        ),
    )
    criteria = SearchCriteria(
        source=DetectionSource.KEYWORD, keywords=(SearchKeyword("全件検索"),)
    )
    workers = ReadWorkers()
    try:
        async with PostgresRuntime(
            pg_engines[1], workers=workers
        ).acquire() as snapshot:
            first = await snapshot.evidence_reader.search(criteria, medicines)
            repeated = await snapshot.evidence_reader.search(criteria, medicines)
            assert len(first) == 450
            assert {item.document_id.value for item in first} == {
                receipt.document_id for receipt in receipts
            }
            assert all("テスト全件検索" in item.excerpt.value for item in first)
            assert [evidence_payload(item) for item in repeated] == [
                evidence_payload(item) for item in first
            ]
    finally:
        await workers.aclose()


@pytest.mark.source_data
@pytest.mark.asyncio
async def test_pg032_original_xml_tables_and_sources_match_independent_oracle(
    pg_engines, pg_publisher
):
    from backend.application.medicine.queries.models import ResolvedMedicine
    from backend.domain.medicine.value_objects import MedicineMatch
    from backend.tests.integration.test_interaction_xml_oracle import (
        assert_public_source,
        get_interaction_oracle,
    )
    from backend.tests.support.interaction_raw_oracle import (
        DOCUMENTS,
        ROOT,
        read_raw_oracle,
    )

    assert read_raw_oracle() == get_interaction_oracle()
    for document_id, _, _ in DOCUMENTS:
        publish(
            pg_publisher,
            next(
                (ROOT / "data/pmda/originals").glob(f"*/{document_id}.xml")
            ).read_bytes(),
        )
    workers = ReadWorkers()
    try:
        async with PostgresRuntime(
            pg_engines[1], workers=workers
        ).acquire() as snapshot:
            for document in get_interaction_oracle():
                medicines = (
                    ResolvedMedicine(
                        MedicineMatch(
                            generic_name=None,
                            brand_names=tuple(BrandName(value) for value in ()),
                            yj_codes=tuple(
                                YjCode(value) for value in (document["yj"],)
                            ),
                            matched_aliases=tuple(MatchedAlias(value) for value in ()),
                        ),
                        (document["document_id"],),
                    ),
                )
                for major in ("10", "16"):
                    criteria = SearchCriteria(
                        source=DetectionSource.LOGIC,
                        section_codes=(SearchSectionCode(major),),
                    )
                    result = await snapshot.evidence_reader.search(criteria, medicines)
                    assert len(result) == 1
                    assert_public_source(evidence_payload(result[0]), document, major)
    finally:
        await workers.aclose()


@pytest.mark.asyncio
async def test_pg032_requested_product_tables_and_version_sources_match_old_snapshot(
    pg_engines, pg_publisher
):
    raw = mixed_source()
    assert hashlib.sha256(raw).hexdigest() == ORACLE["mixed_source_sha256"]
    publish(pg_publisher, raw)
    workers = ReadWorkers()
    try:
        async with PostgresRuntime(pg_engines[1], workers=workers).acquire() as scope:
            for code in ("111111111111", "222222222222"):
                actual = await scope.evidence_reader.search(
                    warning_criteria(), target(code)
                )
                assert [evidence_payload(item) for item in actual] == ORACLE[
                    "products"
                ][code]
                assert ("A値" in actual[0].excerpt.value) is (code == "111111111111")
                assert ("B値" in actual[0].excerpt.value) is (code == "222222222222")
        assert pg_engines[1].pool.checkedout() == 0
    finally:
        await workers.aclose()
