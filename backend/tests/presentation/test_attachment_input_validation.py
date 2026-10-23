"""通信型とDomainのSHA検証を実HTTP経路で分離する。DBは使わない。"""

import pytest
from backend.application.file_upload.commands.models import UploadSpec
from backend.presentation.attachment_import_models import UploadRequest
from backend.presentation.attachment_import_routes import router
from backend.presentation.dependencies import get_import_service
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_presentation_only_checks_sha_is_string():
    assert (
        UploadRequest(
            filename="テスト.xml", byte_size=1, source_sha256="short"
        ).source_sha256
        == "short"
    )


@pytest.mark.parametrize("digest", ["short", "g" * 64, "", "　", 123, False, None])
def test_invalid_upload_metadata_is_422_before_storage(digest):
    app = FastAPI()
    app.include_router(router)

    class NeverStore:
        async def start_upload(self, spec):
            raise AssertionError("invalid metadata must not reach storage")

    app.dependency_overrides[get_import_service] = lambda: NeverStore()
    with TestClient(app) as client:
        response = client.post(
            "/api/attachment-imports/uploads",
            json={"filename": "テスト.xml", "byte_size": 1, "source_sha256": digest},
        )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "invalid_upload"


def test_upload_boundary_uses_domain_sha_normalization():
    app = FastAPI()
    app.include_router(router)
    stored: list[UploadSpec] = []

    class Store:
        async def start_upload(self, spec):
            stored.append(spec)
            return "test-upload"

    app.dependency_overrides[get_import_service] = lambda: Store()
    with TestClient(app) as client:
        response = client.post(
            "/api/attachment-imports/uploads",
            json={
                "filename": "テスト.xml",
                "byte_size": 1,
                "source_sha256": " Ａ" + "A" * 63 + " ",
            },
        )
    assert response.status_code == 201
    assert stored[0].source_sha256 == "a" * 64


@pytest.mark.parametrize(
    "failure,status,conflicts",
    [
        ("UploadConflict", 409, True),
        ("UploadGone", 410, False),
        ("UploadLimitExceeded", 413, False),
        ("UploadStorageError", 500, False),
        ("InvalidUpload", 422, False),
    ],
)
def test_transfer_errors_keep_http_contract(failure, status, conflicts):
    from backend.application.file_upload import errors

    class Service:
        async def finish_upload(self, upload_id):
            raise getattr(errors, failure)("テスト転送失敗", "テストエラー")

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_import_service] = lambda: Service()
    with TestClient(app) as client:
        response = client.post("/api/attachment-imports/uploads/test/complete")
    assert response.status_code == status
    expected: dict[str, object] = {
        "code": "テスト転送失敗",
        "message": "テストエラー",
        "phase": "upload",
    }
    if conflicts:
        expected["conflicts"] = []
    assert response.json()["detail"] == expected
