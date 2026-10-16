"""改訂年月による公開先選択を実SQLiteと原本XMLで検証する。"""

import hashlib

import pytest
from backend.application.attachment_import.import_errors import (
    ImportConflict,
    InvalidAttachment,
)
from backend.application.indexing.index_errors import IndexSourceError
from backend.infrastructure.persistence.registration_publisher import RegistrationInput
from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder
from backend.infrastructure.sources.registration_source import read_registered_snapshot
from backend.tests.test_registration_http import client as client
from backend.tests.test_registration_http import post
from backend.tests.test_registration_publisher import publish, rows, source
from backend.tests.test_registration_publisher import publisher as publisher


def document(month, text, codes=("111111111111",), *, doc="test"):
    return source(text, codes, doc=doc).replace(b"2026-10", month.encode())


@pytest.mark.parametrize("newest_first", [False, True])
def test_latest_revision_is_independent_of_upload_order(publisher, newest_first):
    older = document("2025-12", "旧本文")
    newer = document("2026-01", "新本文")
    first, last = (newer, older) if newest_first else (older, newer)
    first_result = publish(publisher, first)
    result = publish(publisher, last)
    snapshot = read_registered_snapshot(publisher.index_path)
    assert snapshot is not None
    assert all(
        isinstance(unit.payload["text"], str) and "新本文" in unit.payload["text"]
        for unit in snapshot.units
    )
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
    publisher.recover()


def test_each_yj_selects_its_own_latest_revision(publisher):
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
    snapshot = read_registered_snapshot(publisher.index_path)
    assert snapshot is not None
    assert {m.yj_code.value for m in snapshot.medicines if m.yj_code is not None} == {
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
    assert rows(publisher, "SELECT COUNT(*) FROM registration_state") == [(0,)]


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


def test_legacy_registration_order_is_not_silently_republished(publisher):
    old = publish(publisher, document("2025-01", "旧版"))
    newer = publish(publisher, document("2026-01", "新版"))
    # Simulate an existing index whose active pointer was chosen by upload order.
    import sqlite3

    with sqlite3.connect(publisher.index_path) as connection:
        connection.execute(
            "UPDATE active_registrations SET version_id = ?",
            (f"{old.document_id}:{old.source_sha256}",),
        )
    with pytest.raises(IndexSourceError, match="revision_policy_migration_required"):
        read_registered_snapshot(publisher.index_path)
    with pytest.raises(ImportConflict) as failure:
        publisher.recover()
    assert failure.value.code == "revision_policy_migration_required"
    assert rows(publisher, "SELECT version_id FROM active_registrations") == [
        (f"{old.document_id}:{old.source_sha256}",)
    ]
    assert newer.source_sha256 != old.source_sha256


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
