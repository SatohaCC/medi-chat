"""改訂年月による公開先選択を実PostgreSQLと原本XMLで検証する。"""

import hashlib
import json

import pytest
from backend.application.attachment_import.errors import (
    ImportConflict,
    InvalidAttachment,
)
from backend.infrastructure.persistence.queries.postgres_search_snapshot_provider import (
    PostgresRuntime,
)
from backend.infrastructure.persistence.registration.registration_payloads import (
    PostgresRegistrationInput as RegistrationInput,
)
from backend.infrastructure.persistence.runtime.read_workers import ReadWorkers
from backend.infrastructure.persistence.schemas import attachment_tables as schema
from backend.infrastructure.pmda_xml.pmda_xml_decoder import PmdaXmlDecoder
from backend.tests.integration.test_postgres_registration import pg_publisher, publish
from backend.tests.presentation.test_registration_http import client as client
from backend.tests.presentation.test_registration_http import post
from backend.tests.support.postgres_fixtures import pg_engines as pg_engines
from backend.tests.support.registration_oracles import source
from sqlalchemy import select, text

publisher = pg_publisher


def rows(publisher, statement):
    with publisher.engine.connect() as connection:
        return connection.execute(text(statement)).all()


async def medicines(publisher):
    workers = ReadWorkers()
    try:
        async with PostgresRuntime(
            publisher.engine, workers=workers
        ).acquire() as snapshot:
            return await snapshot.medicine_reader.read_medicines()
    finally:
        await workers.aclose()


def document(month, text, codes=("111111111111",), *, doc="test"):
    return source(text, codes, doc=doc).replace(b"2026-10", month.encode())


@pytest.mark.parametrize("newest_first", [False, True])
def test_latest_revision_is_independent_of_upload_order(publisher, newest_first):
    older = document("2025-12", "旧本文")
    newer = document("2026-01", "新本文")
    first, last = (newer, older) if newest_first else (older, newer)
    first_result = publish(publisher, first)
    result = publish(publisher, last)
    with publisher.engine.connect() as connection:
        units = (
            connection.execute(
                select(schema.units.c.payload_json).where(
                    schema.units.c.version_id.in_(select(schema.active.c.version_id))
                )
            )
            .scalars()
            .all()
        )
    assert units and all("新本文" in json.loads(unit)["text"] for unit in units)
    assert rows(
        publisher,
        "SELECT source_sha256 FROM registration_receipts WHERE version_id IN (SELECT version_id FROM active_registrations)",
    ) == [(hashlib.sha256(newer).hexdigest(),)]
    if newest_first:
        assert result.active_yj_codes == ()
        assert not result.search_index_updated
        assert result.generation_id == first_result.generation_id
    repeated = publish(publisher, newer)
    assert repeated.reused and repeated.active_yj_codes == ("111111111111",)
    assert repeated.generation_id == result.generation_id
    publisher.maintenance.cleanup()


@pytest.mark.asyncio
async def test_each_yj_selects_its_own_latest_revision(publisher):
    publish(publisher, document("2026-06", "X最新版", doc="x"))
    publish(publisher, document("2025-01", "Y旧版", ("222222222222",), doc="y"))
    incoming = publish(
        publisher,
        document("2025-12", "XY中間版", ("111111111111", "222222222222"), doc="xy"),
    )
    assert incoming.active_yj_codes == ("222222222222",)
    assert incoming.replaced_yj_codes == ("222222222222",)
    active = rows(
        publisher,
        "SELECT yj_code, version_id FROM active_registrations ORDER BY yj_code",
    )
    assert active[0][1].startswith("000001_x:")
    assert active[1][1] == f"{incoming.document_id}:{incoming.source_sha256}"
    products = await medicines(publisher)
    assert {m.yj_code.value for m in products if m.yj_code is not None} == {
        "111111111111",
        "222222222222",
    }


def test_equal_revision_conflict_is_atomic_for_multiple_yj(publisher):
    publish(publisher, document("2026-06", "既存X", doc="x"))
    old = rows(publisher, "SELECT * FROM active_registrations")
    count = rows(publisher, "SELECT COUNT(*) FROM registration_receipts")
    with pytest.raises(ImportConflict) as failure:
        publish(
            publisher,
            document("2026-06", "異なるXY", ("111111111111", "222222222222"), doc="xy"),
        )
    assert failure.value.code == "same_revision_conflict"
    assert rows(publisher, "SELECT * FROM active_registrations") == old
    assert rows(publisher, "SELECT COUNT(*) FROM registration_receipts") == count


def test_missing_revision_is_rejected_before_any_registration(publisher):
    import re

    value = re.sub(
        b"<DateOfPreparationOrRevision>.*?</DateOfPreparationOrRevision>",
        b"",
        document("2026-01", "本文"),
    )
    with pytest.raises(InvalidAttachment) as failure:
        publish(publisher, value)
    assert failure.value.code == "missing_revision"
    assert rows(publisher, "SELECT COUNT(*) FROM registration_receipts") == [(0,)]
    assert rows(
        publisher, "SELECT generation_id, sequence FROM registration_state"
    ) == [(None, 0)]


@pytest.mark.parametrize("reverse", [False, True])
def test_initial_batch_uses_dates_and_returns_results_in_input_order(
    publisher, reverse
):
    values = [document("2025-01", "旧版"), document("2026-01", "新版")]
    if reverse:
        values.reverse()
    results = publisher.publish_inputs(
        tuple(
            RegistrationInput(PmdaXmlDecoder().decode(value), value) for value in values
        ),
        initial=True,
    )
    assert [r.revisions[0].year_month for r in results] == (
        ["2026-01", "2025-01"] if reverse else ["2025-01", "2026-01"]
    )
    assert [bool(r.active_yj_codes) for r in results] == (
        [True, False] if reverse else [False, True]
    )
    assert [r.registration_sequence for r in results] == [1, 2]
    assert rows(
        publisher,
        "SELECT source_sha256 FROM registration_receipts ORDER BY sequence",
    ) == [(hashlib.sha256(value).hexdigest(),) for value in values]


def test_batch_receipts_keep_input_order_with_obsolete_ambiguity_and_retries(publisher):
    values = [
        document("2025-01", "旧版A"),
        document("2025-01", "旧版B"),
        document("2026-01", "最新版"),
    ]
    inputs = tuple(
        RegistrationInput(PmdaXmlDecoder().decode(value), value) for value in values
    )
    results = publisher.publish_inputs(inputs + (inputs[0],), initial=True)
    assert [r.registration_sequence for r in results] == [1, 2, 3, 1]
    assert [r.reused for r in results] == [False, False, False, True]
    assert [bool(r.active_yj_codes) for r in results] == [False, False, True, False]
    repeated = publisher.publish_inputs(inputs)
    assert [r.registration_sequence for r in repeated] == [1, 2, 3]
    assert all(r.reused for r in repeated)
    assert rows(publisher, "SELECT COUNT(*) FROM registration_receipts") == [(3,)]


@pytest.mark.asyncio
async def test_http_reports_older_upload_conflict_and_missing_date(client):
    import re

    first = await post(client, document("2026-01", "最新本文"))
    assert first.status_code == 201
    original_generation = first.json()["generation_id"]
    older = await post(client, document("2025-12", "古い本文"))
    assert older.status_code == 201
    assert older.json()["status"] == "superseded"
    assert older.json()["search_index_updated"] is False
    assert older.json()["generation_id"] == original_generation
    conflicting = await post(client, document("2026-01", "同年月の別原本"))
    assert conflicting.status_code == 409
    assert conflicting.json()["detail"]["code"] == "same_revision_conflict"
    missing = re.sub(
        b"<DateOfPreparationOrRevision>.*?</DateOfPreparationOrRevision>",
        b"",
        document("2026-02", "日付欠落"),
    )
    response = await post(client, missing)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "missing_revision"
