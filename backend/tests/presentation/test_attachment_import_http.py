import hashlib
from dataclasses import replace

import httpx
import pytest
import pytest_asyncio
from backend.application.attachment_import.import_document import (
    AttachmentImportService,
)
from backend.application.attachment_import.import_errors import (
    ImportConflict,
    ImportLimitExceeded,
    ImportStorageError,
)
from backend.infrastructure.persistence.attachment_import_store import (
    FileAttachmentImportStore,
)
from backend.infrastructure.pmda_xml.artifact_mapping import (
    MAX_ARTIFACT_BYTES,
    PmdaArtifactEncoder,
)
from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder
from backend.presentation.attachment_import_routes import router
from backend.tests.support.attachment_import_fixtures import xml_source
from fastapi import FastAPI


@pytest_asyncio.fixture
async def client(tmp_path):
    service = AttachmentImportService(
        decoder=PmdaXmlDecoder(),
        encoder=PmdaArtifactEncoder(),
        store=FileAttachmentImportStore(tmp_path),
    )
    app = FastAPI()
    app.state.attachment_import_service = service
    app.include_router(router)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
    await service.aclose()


@pytest.mark.asyncio
async def test_upload_get_and_resend(client):
    source = xml_source()
    response = await client.post(
        "/api/attachment-imports",
        files={"file": ("odd.bin", source, "application/octet-stream")},
    )
    assert response.status_code == 201
    result = response.json()
    assert result["source_sha256"] == hashlib.sha256(source).hexdigest()
    assert result["status"] == "stored" and result["reused"] is False
    assert result["search_index_updated"] is False
    assert result["section_count"] == result["search_unit_count"] == 1
    assert result["products"] == [{"yj_code": "111111111111", "brand_name": "製品A"}]
    assert (await client.get(response.headers["location"])).json() == result
    repeated = await client.post(
        "/api/attachment-imports", files={"file": ("other.xml", source)}
    )
    assert repeated.status_code == 200 and repeated.json()["reused"] is True
    assert repeated.headers["location"] == response.headers["location"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "files",
    [
        [],
        [("file", ("empty.xml", b""))],
        [("file", ("a", b"x")), ("other", ("b", b"x"))],
    ],
)
async def test_file_count_and_empty_are_400(client, files):
    response = await client.post("/api/attachment-imports", files=files)
    assert response.status_code == 400
    assert set(response.json()["detail"]) == {"code", "message", "phase"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source,status",
    [
        (b"PK\x03\x04binary", 415),
        (b"<PackIns>", 422),
        (xml_source(prefix='<!DOCTYPE PackIns [<!ENTITY x "bad">]>'), 422),
    ],
)
async def test_content_errors_have_uniform_details(client, source, status):
    response = await client.post(
        "/api/attachment-imports", files={"file": ("input.xml", source)}
    )
    assert response.status_code == status
    assert set(response.json()["detail"]) == {"code", "message", "phase"}


@pytest.mark.asyncio
async def test_missing_version_is_404(client):
    response = await client.get("/api/attachment-imports/unknown/" + "a" * 64)
    assert response.status_code == 404
    assert set(response.json()["detail"]) == {"code", "message", "phase"}


@pytest.mark.asyncio
@pytest.mark.parametrize("extra,status", [(0, 201), (1, 413)])
async def test_file_actual_byte_boundary(client, extra, status):
    source = xml_source()
    source = b" " * (10 * 1024 * 1024 - len(source) + extra) + source
    response = await client.post(
        "/api/attachment-imports", files={"file": ("input.xml", source)}
    )
    assert response.status_code == status


@pytest.mark.asyncio
@pytest.mark.parametrize("length", [None, "1"])
@pytest.mark.parametrize("extra", [0, 1])
async def test_total_actual_stream_boundary_before_multipart(client, length, extra):
    async def chunks():
        remaining = 11 * 1024 * 1024 + extra
        while remaining:
            chunk = b"x" * min(65536, remaining)
            remaining -= len(chunk)
            yield chunk

    headers = {"content-type": "application/octet-stream"}
    if length is not None:
        headers["content-length"] = length
    response = await client.post(
        "/api/attachment-imports", content=chunks(), headers=headers
    )
    assert response.status_code == (413 if extra else 400)
    assert response.json()["detail"]["code"] == (
        "request_too_large" if extra else "file_required"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure,status",
    [
        (ImportConflict("storage_conflict", "Stored import is inconsistent"), 409),
        (ImportStorageError("storage_error", "Import storage is unavailable"), 500),
        (ImportLimitExceeded("output_too_large", "Artifacts exceed limit"), 413),
    ],
)
async def test_application_failures_map_without_raw_exception(
    client, monkeypatch, failure, status
):
    def encode(self, *args, **kwargs):
        raise failure

    monkeypatch.setattr(PmdaArtifactEncoder, "encode", encode)
    for _ in range(2):
        response = await client.post(
            "/api/attachment-imports", files={"file": ("a.xml", xml_source())}
        )
        assert response.status_code == status
        assert response.json() == {
            "detail": {
                "code": failure.code,
                "message": failure.message,
                "phase": failure.phase,
                **({"conflicts": []} if status == 409 else {}),
            }
        }


@pytest.mark.asyncio
async def test_malformed_and_excess_multipart_have_uniform_errors(client):
    response = await client.post(
        "/api/attachment-imports",
        content=b"bad",
        headers={"content-type": "multipart/form-data"},
    )
    assert response.status_code == 400
    assert set(response.json()["detail"]) == {"code", "message", "phase"}
    response = await client.post(
        "/api/attachment-imports", files=[("file", ("a", b"x"))] * 3
    )
    assert response.status_code == 400
    assert set(response.json()["detail"]) == {"code", "message", "phase"}


def test_new_openapi_contract_is_explicit():
    app = FastAPI()
    app.include_router(router)
    schema = app.openapi()
    post = schema["paths"]["/api/attachment-imports"]["post"]
    assert post["requestBody"]["content"]["multipart/form-data"]["schema"][
        "properties"
    ]["file"] == {"type": "string", "format": "binary"}
    assert "201" in post["responses"]
    assert schema["components"]["schemas"]["AttachmentImportResponse"]["required"] == [
        "document_id",
        "source_sha256",
        "status",
        "reused",
        "validation_status",
        "section_count",
        "search_unit_count",
        "products",
        "revisions",
        "warnings",
        "search_index_updated",
        "generation_id",
        "registration_sequence",
        "active_yj_codes",
        "replaced_yj_codes",
        "deleted_version_ids",
        "cleanup_pending",
        "artifacts_deleted",
    ]


@pytest.mark.asyncio
async def test_document_id_is_opaque_and_location_roundtrips_without_file_paths(client):
    source = xml_source().replace(
        b"<PackageInsertNo>test</PackageInsertNo>",
        b"<PackageInsertNo>../../outside</PackageInsertNo>",
    )
    response = await client.post(
        "/api/attachment-imports", files={"file": ("../../secret.xml", source)}
    )
    assert response.status_code == 201
    assert (await client.get(response.headers["location"])).json() == response.json()


@pytest.mark.asyncio
@pytest.mark.parametrize("depth,status", [(256, 201), (257, 422)])
async def test_depth_through_http(client, depth, status):
    source = xml_source(
        "<Warnings>"
        + "<Detail>" * (depth - 3)
        + "<Lang>本文</Lang>"
        + "</Detail>" * (depth - 3)
        + "</Warnings>"
    )
    response = await client.post(
        "/api/attachment-imports", files={"file": ("a.xml", source)}
    )
    assert response.status_code == status
    if status == 422:
        assert response.json()["detail"]["code"] == "xml_depth_limit"


@pytest.mark.asyncio
@pytest.mark.parametrize("count,status", [(200000, 201), (200001, 422)])
async def test_element_count_through_http(client, count, status):
    import xml.etree.ElementTree as ET

    source = xml_source()
    header = sum(1 for _ in ET.fromstring(source).iter())
    source = source.replace(
        b"</Warnings>",
        b"<Empty/>" * (count - header) + b"<?test pi?><!--comment--></Warnings>",
    )
    response = await client.post(
        "/api/attachment-imports", files={"file": ("a.xml", source)}
    )
    assert response.status_code == status
    if status == 422:
        assert response.json()["detail"]["code"] == "xml_element_limit"


@pytest.mark.asyncio
@pytest.mark.parametrize("extra,status", [(0, 201), (1, 413)])
async def test_actual_output_byte_boundary_through_http(
    client, monkeypatch, extra, status
):
    original = PmdaArtifactEncoder.encode

    def padded(self, *args, **kwargs):
        bundle = original(self, *args, **kwargs)
        measured = sum(
            len(file.content)
            for file in bundle.files
            if file.name != "source_metadata.json"
        )
        files = tuple(
            replace(
                file,
                content=file.content + b" " * (MAX_ARTIFACT_BYTES - measured + extra),
            )
            if file.name == "document.json"
            else file
            for file in bundle.files
        )
        assert (
            sum(
                len(file.content)
                for file in files
                if file.name != "source_metadata.json"
            )
            == MAX_ARTIFACT_BYTES + extra
        )
        return replace(bundle, files=files)

    monkeypatch.setattr(PmdaArtifactEncoder, "encode", padded)
    response = await client.post(
        "/api/attachment-imports", files={"file": ("a.xml", xml_source())}
    )
    assert response.status_code == status
    if status == 201:
        assert (await client.get(response.headers["location"])).status_code == 200


@pytest.mark.asyncio
async def test_real_storage_fault_and_corruption_are_private_and_preserve_versions(
    client, tmp_path, monkeypatch
):
    first = await client.post(
        "/api/attachment-imports", files={"file": ("a.xml", xml_source())}
    )
    assert first.status_code == 201
    location = first.headers["location"]
    original = FileAttachmentImportStore._write_file

    def fail(path, content):
        raise OSError("private C:/secret/capacity-or-permission")

    monkeypatch.setattr(FileAttachmentImportStore, "_write_file", staticmethod(fail))
    failed = await client.post(
        "/api/attachment-imports",
        files={"file": ("b.xml", xml_source("<Warnings><Lang>別版</Lang></Warnings>"))},
    )
    assert failed.status_code == 500
    assert failed.json() == {
        "detail": {
            "code": "storage_error",
            "message": "Import could not be saved",
            "phase": "validation",
        }
    }
    assert "secret" not in failed.text
    assert not list(tmp_path.glob(".stage-*"))
    assert (await client.get(location)).status_code == 200
    monkeypatch.setattr(
        FileAttachmentImportStore, "_write_file", staticmethod(original)
    )
    (document,) = tmp_path.rglob("document.json")
    document.write_bytes(b"corrupt")
    for response in [
        await client.get(location),
        await client.post(
            "/api/attachment-imports", files={"file": ("a.xml", xml_source())}
        ),
    ]:
        assert response.status_code == 409
        assert set(response.json()["detail"]) == {
            "code",
            "message",
            "phase",
            "conflicts",
        }
    assert document.read_bytes() == b"corrupt"
