"""TC070: HTTP publication preserves unrelated YJs and restart-visible evidence."""

from dataclasses import dataclass

import httpx
import pytest
from backend.application.indexing.values import SearchSectionCode
from backend.application.retrieval.queries.models import SearchCriteria
from backend.application.retrieval.values import DetectionSource
from backend.tests.integration.test_generation_readonly import digest
from backend.tests.support.attachment_import_fixtures import xml_source
from backend.tests.support.postgres_fixtures import pg_api as pg_api
from backend.tests.support.postgres_fixtures import pg_engines as pg_engines


@dataclass(frozen=True)
class SearchTarget:
    document_ids: tuple[str, ...]
    yj_codes: tuple[str, ...]


async def search(app, criteria, targets):
    async with app.state.generation_runtime.acquire() as snapshot:
        return await snapshot.evidence_reader.search(criteria, targets)


@pytest.mark.asyncio
async def test_http_import_and_restart_preserve_search_snapshot(pg_api, pg_engines):
    criteria = SearchCriteria(
        source=DetectionSource.LOGIC, section_codes=(SearchSectionCode("11"),)
    )
    known = SearchTarget(("test_001",), ("1234567A0000",))
    location = ""
    previous = ()
    saved = digest(pg_engines[0])
    for iteration in range(2):
        app = pg_api()
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client,
        ):
            found = await search(app, criteria, (known,))
            assert len(found) == 1
            assert all(f"記載{i}" in found[0].excerpt.value for i in range(3))
            if iteration == 0:
                previous = found
                invalid = await client.post(
                    "/api/attachment-imports",
                    files={
                        "file": (
                            "missing-yj.xml",
                            xml_source().replace(b"111111111111", b""),
                        )
                    },
                )
                assert invalid.status_code == 422
                assert invalid.json()["detail"]["code"] == "missing_or_invalid_yj"
                assert digest(pg_engines[0]) == saved
                response = await client.post(
                    "/api/attachment-imports",
                    files={
                        "file": (
                            "new.xml",
                            xml_source(
                                "<AdverseEvents><Detail><Lang>新薬の副作用</Lang></Detail></AdverseEvents>"
                            ),
                        )
                    },
                )
                assert response.status_code == 201
                result = response.json()
                assert result["search_index_updated"] is True
                location = response.headers["location"]
                unknown = SearchTarget((result["document_id"],), ("111111111111",))
                imported = await search(app, criteria, (unknown,))
                assert len(imported) == 1
                assert "新薬の副作用" in imported[0].excerpt.value
                assert await search(app, criteria, (known,)) == previous
                saved = digest(pg_engines[0])
            else:
                assert (await client.get(location)).status_code == 200
                assert found == previous
            assert (await client.get("/health")).status_code == 200
        assert digest(pg_engines[0]) == saved
        with pytest.raises(RuntimeError, match="Import service is closed"):
            await app.state.attachment_import_queries.read_result("missing", "a" * 64)
