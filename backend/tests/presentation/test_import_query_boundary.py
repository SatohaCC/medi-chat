"""参照HTTPはCommandを要求せず、Command結果と独立したDTOを返す。"""

from dataclasses import fields, replace
from unittest.mock import Mock

import httpx
import pytest
from backend.application.attachment_import.commands.models import (
    ImportedRevision,
    ImportResult,
    ImportWarning,
)
from backend.application.attachment_import.queries.dtos.import_views import (
    ImportDetail,
    ImportPage,
    ImportProductView,
    ImportRevisionView,
    ImportWarningView,
)
from backend.application.attachment_import.queries.import_history import (
    ImportHistoryQueries,
)
from backend.infrastructure.persistence.import_workers import ImportWorkers
from backend.infrastructure.persistence.postgres_import_queries import (
    PostgresImportQueries,
)
from backend.presentation.attachment_import_routes import router
from backend.presentation.dependencies import get_import_queries, get_import_service
from backend.tests.support.attachment_import_fixtures import encoded, xml_source
from fastapi import FastAPI


def test_query_projection_preserves_receipt_without_sharing_command_dtos():
    stored = replace(
        encoded(xml_source()).result,
        registration_sequence=7,
        revisions=(ImportedRevision("テスト改訂", "2026-10", "1"),),
        warnings=(ImportWarning("テスト警告", "テスト参照"),),
        active_yj_codes=("111111111111",),
        replaced_yj_codes=("222222222222",),
        deleted_version_ids=("テスト旧版",),
        cleanup_pending=(("テスト保留版", "cleanup_required"),),
        generation_id="テスト世代",
        artifacts_deleted=True,
    )
    reader = PostgresImportQueries(Mock())
    reader.result = Mock(return_value=stored)
    detail = reader.read_result(stored.document_id, stored.source_sha256)

    reader.result.assert_called_once_with(
        f"{stored.document_id}:{stored.source_sha256}", get=True
    )
    assert type(detail) is ImportDetail
    assert not isinstance(detail, ImportResult)
    for field in fields(stored):
        if field.name not in {"products", "revisions", "warnings"}:
            assert getattr(detail, field.name) == getattr(stored, field.name)
    assert all(type(product) is ImportProductView for product in detail.products)
    assert all(type(revision) is ImportRevisionView for revision in detail.revisions)
    assert all(type(warning) is ImportWarningView for warning in detail.warnings)
    assert [(w.code, w.reference) for w in detail.warnings] == [
        ("テスト警告", "テスト参照")
    ]
    assert [(r.source_label, r.year_month, r.version) for r in detail.revisions] == [
        ("テスト改訂", "2026-10", "1")
    ]
    assert [(p.yj_code, p.brand_name) for p in detail.products] == [
        (p.yj_code, p.brand_name) for p in stored.products
    ]


@pytest.mark.asyncio
async def test_import_read_routes_only_inject_query_handler():
    stored = encoded(xml_source()).result
    projection = PostgresImportQueries(Mock())
    projection.result = Mock(return_value=stored)
    detail = projection.read_result(stored.document_id, stored.source_sha256)
    reader = Mock(read_result=Mock(return_value=detail))
    reader.list_imports.return_value = ImportPage(items=(), total_count=0)
    executor = ImportWorkers()
    queries = ImportHistoryQueries(reader=reader, executor=executor)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_import_queries] = lambda: queries

    def no_commands():
        raise AssertionError("Query endpoints must not resolve Command dependencies")

    app.dependency_overrides[get_import_service] = no_commands
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                f"/api/attachment-imports/{stored.document_id}/{stored.source_sha256}"
            )
            assert response.status_code == 200
            assert response.json()["document_id"] == stored.document_id
            response = await client.get("/api/attachment-imports?limit=3&offset=2")
            assert response.status_code == 200
            assert response.json() == {
                "items": [],
                "total_count": 0,
                "limit": 3,
                "offset": 2,
            }
            assert (
                await client.get("/api/attachment-imports?limit=0")
            ).status_code == 422
        reader.read_result.assert_called_once_with(
            stored.document_id, stored.source_sha256
        )
        reader.list_imports.assert_called_once_with(limit=3, offset=2)
    finally:
        await executor.aclose()
