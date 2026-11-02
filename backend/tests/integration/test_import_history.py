import hashlib

import httpx
import pytest
from backend.application.package_insert_import.commands.import_documents import (
    PackageInsertImportCommands,
)
from backend.application.package_insert_import.queries.import_history import (
    ImportHistoryQueries,
)
from backend.infrastructure.document_import.original_document_registration_adapter import (
    OriginalDocumentRegistration,
)
from backend.infrastructure.persistence.queries.postgres_import_query_reader import (
    PostgresImportQueries,
)
from backend.infrastructure.persistence.registration.postgres_registration_publisher import (
    PostgresRegistrationPublisher,
)
from backend.infrastructure.persistence.runtime.import_workers import ImportWorkers
from backend.infrastructure.pmda_xml.pmda_artifact_encoder import PmdaArtifactEncoder
from backend.infrastructure.pmda_xml.pmda_xml_decoder import PmdaXmlDecoder
from backend.presentation.package_insert_import_routes import router
from backend.tests.support.postgres_fixtures import pg_engines as pg_engines
from backend.tests.support.registration_oracles import source
from fastapi import FastAPI
from sqlalchemy import event


@pytest.mark.asyncio
async def test_history_retains_deleted_versions_orders_pages_and_avoids_payloads(
    pg_engines,
):
    engine = pg_engines[1]
    publisher = PostgresRegistrationPublisher(engine, encoder=PmdaArtifactEncoder())
    service = PackageInsertImportCommands(
        executor=ImportWorkers(),
        reader=publisher.results,
        registration=OriginalDocumentRegistration(
            decoder=PmdaXmlDecoder(), publisher=publisher
        ),
    )
    app = FastAPI()
    app.include_router(router)
    app.state.package_insert_import_service = service
    import_queries = PostgresImportQueries(engine)
    app.state.package_insert_import_queries = ImportHistoryQueries(
        reader=import_queries, executor=service._executor
    )
    queries = []

    def capture(_conn, _cursor, statement, _parameters, _context, _many):
        queries.append(statement)

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            empty = (await client.get("/api/package-insert-imports")).json()
            assert empty == {"items": [], "total_count": 0, "limit": 50, "offset": 0}
            old = source("旧版", revised_at="2026-09")
            new = source("新版", revised_at="2026-10")
            for raw in (old, new):
                response = await client.post(
                    "/api/package-insert-imports",
                    files={"file": ("テスト.xml", raw, "text/xml")},
                )
                assert response.status_code == 201
            replay = await client.post(
                "/api/package-insert-imports",
                files={"file": ("再送.xml", new, "text/xml")},
            )
            assert replay.status_code == 200
            event.listen(engine, "before_cursor_execute", capture)
            first_response = await client.get(
                "/api/package-insert-imports?limit=1&offset=0"
            )
            first = first_response.json()
            assert first_response.status_code == 200
            assert first["total_count"] == 2
            item = first["items"][0]
            assert item["filename"] == "テスト.xml"
            assert item["source_sha256"] == hashlib.sha256(new).hexdigest()
            assert item["registration_sequence"] == 2
            assert item["revised_at"] == "2026-10"
            assert item["products"] == [
                {"yj_code": "111111111111", "brand_name": "製品A"}
            ]
            assert item["active_yj_codes"] == ["111111111111"]
            assert item["artifacts_deleted"] is False
            assert all(
                "package_insert_versions.source" not in query
                and "package_insert_versions.structure" not in query
                for query in queries
            )
            assert len(queries) == 4  # read-only setup + count + page + active codes
            second = (
                await client.get("/api/package-insert-imports?limit=1&offset=1")
            ).json()
            old_item = second["items"][0]
            assert old_item["source_sha256"] == hashlib.sha256(old).hexdigest()
            assert old_item["filename"] is None
            assert old_item["active_yj_codes"] == []
            assert old_item["artifacts_deleted"] is True
            assert old_item["products"] == item["products"]
            assert (await client.get("/api/package-insert-imports?offset=2")).json()[
                "items"
            ] == []
            for query in ("limit=0", "limit=101", "offset=-1"):
                assert (
                    await client.get(f"/api/package-insert-imports?{query}")
                ).status_code == 422
    finally:
        if event.contains(engine, "before_cursor_execute", capture):
            event.remove(engine, "before_cursor_execute", capture)
        await service.aclose()
