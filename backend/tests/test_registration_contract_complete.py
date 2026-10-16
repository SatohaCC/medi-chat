import hashlib
import sqlite3
from pathlib import Path

import pytest
from backend.domain.attachment.identifiers import DocumentId
from backend.tests.test_registration_http import client as client
from backend.tests.test_registration_http import post
from backend.tests.test_registration_publisher import publisher as publisher
from backend.tests.test_registration_publisher import snapshot, source


def current_generation(publisher):
    with sqlite3.connect(
        publisher.index_path.as_uri() + "?mode=ro", uri=True
    ) as connection:
        return connection.execute(
            "SELECT generation_id FROM registration_state WHERE singleton=1"
        ).fetchone()[0]


def expected(
    value,
    generation,
    sequence,
    codes,
    *,
    active=None,
    reused=False,
    status="registered",
    replaced=(),
    deleted=(),
    pending=(),
    artifacts_deleted=False,
    revised_at="2026-10",
):
    return {
        "document_id": "000001_test",
        "source_sha256": hashlib.sha256(value).hexdigest(),
        "status": status,
        "reused": reused,
        "validation_status": "pass",
        "section_count": 1,
        "search_unit_count": 1,
        "products": [
            {"yj_code": code, "brand_name": "製品A" if i == 0 else "B薬"}
            for i, code in enumerate(codes)
        ],
        "revisions": [
            {"source_label": "今回", "year_month": revised_at, "version": "1"}
        ],
        "warnings": [],
        "search_index_updated": bool(codes if active is None else active),
        "generation_id": generation,
        "registration_sequence": sequence,
        "active_yj_codes": list(codes if active is None else active),
        "replaced_yj_codes": list(replaced),
        "deleted_version_ids": list(deleted),
        "cleanup_pending": [
            {"version_id": version, "reason": reason} for version, reason in pending
        ],
        "artifacts_deleted": artifacts_deleted,
    }


@pytest.mark.asyncio
async def test_tc106_all_registration_dtos_have_fixed_complete_fields(
    client, publisher, monkeypatch
):
    a, b = "111111111111", "222222222222"
    old = source("O共通", (a, b))
    old_id = f"000001_test:{hashlib.sha256(old).hexdigest()}"
    url = f"/api/attachment-imports/000001_test/{hashlib.sha256(old).hexdigest()}"
    response = await post(client, old)
    assert response.status_code == 201, response.text
    assert response.json() == expected(old, current_generation(publisher), 1, (a, b))
    stored = (
        publisher.store._target(
            DocumentId("000001_test"), hashlib.sha256(old).hexdigest()
        )
        / "result.json"
    )
    saved = stored.read_bytes()
    repeat = await post(client, old)
    assert repeat.status_code == 200
    assert repeat.json() == expected(
        old, current_generation(publisher), 1, (a, b), reused=True
    )
    new_a = source("N A更新", revised_at="2026-11")
    response = await post(client, new_a)
    assert response.status_code == 201, response.text
    assert response.json() == expected(
        new_a,
        current_generation(publisher),
        2,
        (a,),
        replaced=(a,),
        revised_at="2026-11",
    )
    assert (await client.get(url)).json() == expected(
        old, current_generation(publisher), 1, (a, b), active=(b,)
    )
    repeat = await post(client, old)
    assert repeat.status_code == 200
    assert repeat.json() == expected(
        old, current_generation(publisher), 1, (a, b), active=(b,), reused=True
    )
    assert stored.read_bytes() == saved
    original_unlink = Path.unlink

    def fail(path, *args, **kwargs):
        if path.parent == stored.parent:
            raise PermissionError("fixed pending IO")
        return original_unlink(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", fail)
        new_b = source("P B更新", (b,), revised_at="2026-11")
        response = await post(client, new_b)
        assert response.status_code == 201, response.text
        assert response.json() == expected(
            new_b,
            current_generation(publisher),
            3,
            (b,),
            replaced=(b,),
            pending=((old_id, "io_error"),),
            status="registered_cleanup_pending",
            revised_at="2026-11",
        )
        assert (await client.get(url)).json() == expected(
            old,
            current_generation(publisher),
            1,
            (a, b),
            active=(),
            status="superseded",
        )
        assert stored.read_bytes() == saved
    repeat = await post(client, new_b)
    assert repeat.status_code == 200
    assert repeat.json() == expected(
        new_b,
        current_generation(publisher),
        3,
        (b,),
        reused=True,
        replaced=(b,),
        deleted=(old_id,),
        revised_at="2026-11",
    )
    old_repeat = await post(client, old)
    assert old_repeat.status_code == 200
    assert old_repeat.json() == expected(
        old,
        current_generation(publisher),
        1,
        (a, b),
        active=(),
        reused=True,
        status="superseded",
        artifacts_deleted=True,
    )
    gone = await client.get(url)
    assert gone.status_code == 410
    assert gone.json() == {
        "detail": {
            "code": "version_deleted",
            "message": "Registered version artifacts have been deleted",
            "phase": "publication",
        }
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "files,status,code,message",
    [
        ([], 400, "file_required", "XMLファイルを1つ選択してください。"),
        (
            [("file", ("empty.xml", b"", "application/xml"))],
            400,
            "empty_file",
            "空のファイルは取り込めません。",
        ),
        (
            [("file", ("fake.xml", b"PKbinary", "application/xml"))],
            415,
            "unsupported_input",
            "Input is not supported XML",
        ),
        (
            [
                (
                    "file",
                    (
                        "dtd.xml",
                        b'<!DOCTYPE PackIns [<!ENTITY x "bad">]>' + source("DTD"),
                        "application/xml",
                    ),
                )
            ],
            422,
            "xml_forbidden_declaration",
            "DTD and entity declarations are not supported",
        ),
        (
            [("file", ("large.xml", b"x" * (10 * 1024 * 1024 + 1), "application/xml"))],
            413,
            "source_too_large",
            "XMLファイルが上限を超えています。",
        ),
    ],
)
async def test_tc107_old_input_boundaries_real_publisher_preserve_snapshot(
    client, publisher, files, status, code, message
):
    assert (await post(client, source("旧公開"))).status_code == 201
    before = snapshot(publisher)
    response = await client.post("/api/attachment-imports", files=files)
    assert response.status_code == status
    assert response.json() == {
        "detail": {"code": code, "message": message, "phase": "validation"}
    }
    assert snapshot(publisher) == before
