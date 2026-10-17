import hashlib
import re

import httpx
import pytest
import pytest_asyncio
from backend.application.attachment_import.import_document import (
    AttachmentImportService,
)
from backend.infrastructure.pmda_xml.artifact_mapping import PmdaArtifactEncoder
from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder
from backend.presentation.attachment_import_routes import router
from backend.tests.integration.test_registration_publisher import (
    publisher as publisher,
)
from backend.tests.integration.test_registration_publisher import (
    snapshot,
    source,
)
from backend.tests.support.attachment_import_fixtures import encoded
from fastapi import FastAPI


@pytest_asyncio.fixture
async def client(publisher):
    service = AttachmentImportService(
        decoder=PmdaXmlDecoder(),
        encoder=PmdaArtifactEncoder(),
        store=publisher.store,
        publisher=publisher,
    )
    app = FastAPI()
    app.include_router(router)
    app.state.attachment_import_service = service
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
    await service.aclose()


async def post(client, value):
    return await client.post(
        "/api/attachment-imports",
        files={"file": ("source.xml", value, "application/xml")},
    )


@pytest.mark.asyncio
async def test_tc106_113_unregistered_store_is_private_then_first_receipt_published(
    client, publisher
):
    value = source("stored以前")
    bundle = encoded(value)
    publisher.store.commit(bundle, value)
    original = {
        file.name: publisher.store._target(bundle.document_id, bundle.source_sha256)
        .joinpath(file.name)
        .read_bytes()
        for file in bundle.files
    }
    url = f"/api/attachment-imports/000001_test/{hashlib.sha256(value).hexdigest()}"
    assert (await client.get(url)).status_code == 404
    response = await post(client, value)
    assert response.status_code == 201
    result = response.json()
    assert re.fullmatch("[0-9a-f]{32}", result["generation_id"])
    assert result == {
        "document_id": "000001_test",
        "source_sha256": hashlib.sha256(value).hexdigest(),
        "status": "registered",
        "reused": False,
        "validation_status": "pass",
        "section_count": 1,
        "search_unit_count": 1,
        "products": [{"yj_code": "111111111111", "brand_name": "製品A"}],
        "revisions": [
            {"source_label": "今回", "year_month": "2026-10", "version": "1"}
        ],
        "warnings": [],
        "search_index_updated": True,
        "generation_id": result["generation_id"],
        "registration_sequence": 1,
        "active_yj_codes": ["111111111111"],
        "replaced_yj_codes": [],
        "deleted_version_ids": [],
        "cleanup_pending": [],
        "artifacts_deleted": False,
    }
    assert result["status"] == "registered" and result["search_index_updated"] is True
    assert result["registration_sequence"] == 1 and result["active_yj_codes"] == [
        "111111111111"
    ]
    assert (
        result["generation_id"]
        and result["replaced_yj_codes"] == []
        and result["cleanup_pending"] == []
    )
    assert {
        file.name: publisher.store._target(bundle.document_id, bundle.source_sha256)
        .joinpath(file.name)
        .read_bytes()
        for file in bundle.files
    } == original
    repeat = await post(client, value)
    assert repeat.status_code == 200 and repeat.json()["reused"] is True
    assert (
        repeat.json()["generation_id"] == result["generation_id"]
        and repeat.json()["registration_sequence"] == 1
    )


@pytest.mark.asyncio
async def test_tc106_old_deleted_receipt_post_never_recreates_files_get_is_gone(
    client, publisher
):
    old = source("旧版")
    new = source("新版", revised_at="2026-11")
    assert (await post(client, old)).status_code == 201
    assert (await post(client, new)).status_code == 201
    result = await post(client, old)
    assert result.status_code == 200
    payload = result.json()
    assert payload["status"] == "superseded" and payload["artifacts_deleted"] is True
    assert payload["search_index_updated"] is False and payload["active_yj_codes"] == []
    assert payload["registration_sequence"] == 1
    gone = await client.get(
        f"/api/attachment-imports/000001_test/{hashlib.sha256(old).hexdigest()}"
    )
    assert (
        gone.status_code == 410 and gone.json()["detail"]["code"] == "version_deleted"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "value,status,code",
    [
        (b"not xml", 415, "unsupported_input"),
        (source("invalid").replace(b"111111111111", b""), 422, "missing_or_invalid_yj"),
    ],
)
async def test_tc107_validation_error_phase_and_no_publication(
    client, publisher, value, status, code
):
    before = snapshot(publisher)
    response = await post(client, value)
    assert response.status_code == status
    assert response.json()["detail"]["code"] == code
    assert response.json()["detail"]["phase"] == "validation"
    assert snapshot(publisher) == before


def test_tc106_107_openapi_declares_reuse_and_conflict_metadata():
    app = FastAPI()
    app.include_router(router)
    schema = app.openapi()
    responses = schema["paths"]["/api/attachment-imports"]["post"]["responses"]
    assert set(responses) == {"200", "201", "400", "409", "413", "415", "422", "500"}
    components = schema["components"]["schemas"]
    assert responses["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/AttachmentImportResponse"
    }
    assert responses["409"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ImportConflictResponse"
    }
    assert set(components["ImportConflictDetail"]["required"]) == {
        "code",
        "message",
        "phase",
        "conflicts",
    }
    assert set(components["ImportConflictItem"]["required"]) == {
        "yj_code",
        "version_ids",
    }


@pytest.mark.asyncio
async def test_tc107_artifact_conflict_has_declared_list_and_preserves_old_publication(
    client, publisher
):
    from backend.application.attachment_import.import_errors import ImportConflict

    assert (await post(client, source("旧公開"))).status_code == 201
    before = snapshot(publisher)

    def conflict(phase):
        if phase == "artifacts":
            raise ImportConflict(
                "source_hash_conflict", "Source artifact conflicts", phase="artifact"
            )

    publisher.fault = conflict
    response = await post(client, source("衝突新版", revised_at="2026-11"))
    assert response.status_code == 409
    assert response.json()["detail"] == {
        "code": "source_hash_conflict",
        "message": "Source artifact conflicts",
        "phase": "artifact",
        "conflicts": [],
    }
    assert snapshot(publisher) == before


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fault_phase,expected_phase",
    [
        ("artifacts", "artifact"),
        ("index", "projection"),
        ("transaction", "publication"),
    ],
)
async def test_tc107_build_failure_returns_stable_phase_and_old_snapshot(
    client, publisher, fault_phase, expected_phase
):
    assert (await post(client, source("旧公開"))).status_code == 201
    before = snapshot(publisher)

    def fail(phase):
        if phase == fault_phase:
            raise OSError("fixed build failure")

    publisher.fault = fail
    response = await post(client, source("失敗する新版", revised_at="2026-11"))
    assert response.status_code == 500
    assert response.json()["detail"] == {
        "code": "registration_failed",
        "message": "Registration could not be published",
        "phase": expected_phase,
    }
    assert snapshot(publisher) == before


@pytest.mark.asyncio
async def test_tc106_partial_b_and_cleanup_pending_public_metadata(
    client, publisher, monkeypatch
):
    from pathlib import Path

    old = source("旧共通", ("111111111111", "222222222222"))
    first = await post(client, old)
    assert first.status_code == 201
    new_a = await post(client, source("新A", revised_at="2026-11"))
    assert new_a.status_code == 201
    old_url = f"/api/attachment-imports/000001_test/{hashlib.sha256(old).hexdigest()}"
    partial = (await client.get(old_url)).json()
    assert partial["status"] == "registered"
    assert partial["active_yj_codes"] == ["222222222222"]
    assert partial["registration_sequence"] == 1
    assert partial["artifacts_deleted"] is False
    unlink = Path.unlink

    def fail(path, *args, **kwargs):
        if path.name == "source.xml" and path.read_bytes() == old:
            raise PermissionError("fixed cleanup failure")
        return unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail)
    new_b = source("新B", ("222222222222",), revised_at="2026-11")
    pending = await post(client, new_b)
    assert pending.status_code == 201
    payload = pending.json()
    assert payload["status"] == "registered_cleanup_pending"
    assert payload["search_index_updated"] is True
    assert payload["active_yj_codes"] == ["222222222222"]
    assert payload["replaced_yj_codes"] == ["222222222222"]
    assert payload["registration_sequence"] == 3
    assert payload["cleanup_pending"] == [
        {
            "version_id": f"000001_test:{hashlib.sha256(old).hexdigest()}",
            "reason": "io_error",
        }
    ]
    assert (await client.get(old_url)).status_code == 200
    monkeypatch.setattr(Path, "unlink", unlink)
    retry = await post(client, new_b)
    assert retry.status_code == 200
    finished = retry.json()
    assert finished["status"] == "registered"
    assert finished["generation_id"] == payload["generation_id"]
    assert finished["registration_sequence"] == 3
    assert finished["deleted_version_ids"] == [
        f"000001_test:{hashlib.sha256(old).hexdigest()}"
    ]
    assert (await client.get(old_url)).status_code == 410
