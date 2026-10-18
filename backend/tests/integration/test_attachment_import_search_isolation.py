"""TC070 v5: HTTP registration updates search while preserving unrelated YJs."""

import hashlib
from dataclasses import dataclass

import httpx
import pytest
from backend.domain.retrieval.primitives import DetectionSource, SearchSectionCode
from backend.domain.retrieval.value_objects import SearchCriteria
from backend.main import create_app
from backend.tests.support.attachment_import_e2e_server import prepare_root
from backend.tests.support.attachment_import_fixtures import xml_source


@dataclass(frozen=True)
class SearchTarget:
    document_ids: tuple[str, ...]
    yj_codes: tuple[str, ...]


def hashes(root):
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file()
    }


@pytest.mark.asyncio
async def test_http_import_and_restart_preserve_search_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDI_CHAT_ORIGINALS_DIR", str(tmp_path / "originals"))
    structured, index = prepare_root(tmp_path)
    before = hashes(structured)
    index_hash = hashlib.sha256(index.read_bytes()).hexdigest()
    criteria = SearchCriteria(
        source=DetectionSource.LOGIC, section_codes=(SearchSectionCode("11"),)
    )
    known = SearchTarget(("test_001",), ("1234567A0000",))
    location = ""
    previous = ()
    for iteration in range(2):
        app = create_app(structured, index, import_directory=tmp_path / "imports")
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client,
        ):
            found = await app.state.evidence_reader.search(criteria, (known,))
            assert len(found) == 1
            assert all(f"記載{i}" in found[0].excerpt for i in range(3))
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
                assert hashlib.sha256(index.read_bytes()).hexdigest() == index_hash
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
                imported = await app.state.evidence_reader.search(criteria, (unknown,))
                assert len(imported) == 1
                assert "新薬の副作用" in imported[0].excerpt
                assert (
                    await app.state.evidence_reader.search(criteria, (known,))
                    == previous
                )
            else:
                assert (await client.get(location)).status_code == 200
                assert found == previous
            assert (await client.get("/health")).status_code == 200
        assert hashes(structured) == before
        if iteration == 0:
            index_hash = hashlib.sha256(index.read_bytes()).hexdigest()
        else:
            assert hashlib.sha256(index.read_bytes()).hexdigest() == index_hash
        with pytest.raises(RuntimeError, match="Import service is closed"):
            await app.state.attachment_import_service.read_result("missing", "a" * 64)
