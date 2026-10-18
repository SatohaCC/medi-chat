"""HTTP registration keeps originals outside the configured structured directory."""

from backend.infrastructure.persistence.attachment_import_store import (
    FileAttachmentImportStore,
)
from backend.infrastructure.persistence.registration_publisher import (
    RegistrationInput,
    SqliteRegistrationPublisher,
)
from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder
from backend.tests.infrastructure.persistence.test_alembic_migrations import (
    _migrate_database,
)
from backend.tests.integration.test_registration_publisher import source
from fastapi.testclient import TestClient


def test_http_import_preserves_separately_located_initial_original(
    tmp_path, monkeypatch
):
    from backend.main import create_app

    originals = tmp_path / "originals"
    originals.mkdir()
    structured = tmp_path / "current" / "structured"
    structured.mkdir(parents=True)
    index = structured.parent / "index.sqlite3"
    imports = structured.parent / "imports"
    _migrate_database(index, structured)
    original = originals / "initial.xml"
    original.write_bytes(source("テスト既存原本"))
    publisher = SqliteRegistrationPublisher(
        index, FileAttachmentImportStore(imports), allowed_roots=(originals, structured)
    )
    publisher.publish_inputs(
        (
            RegistrationInput(
                PmdaXmlDecoder().decode(original.read_bytes()),
                original.read_bytes(),
                (original,),
                original,
            ),
        ),
        initial=True,
    )
    monkeypatch.setenv("MEDI_CHAT_ORIGINALS_DIR", str(originals))
    app = create_app(structured, index, import_directory=imports)
    with TestClient(app) as client:
        response = client.post(
            "/api/attachment-imports",
            files={
                "file": (
                    "new.xml",
                    source("テスト追加原本", ("222222222222",), doc="new"),
                    "application/xml",
                )
            },
        )
        assert response.status_code == 201, response.text
        assert response.json()["status"] == "registered"
        assert original.read_bytes() == source("テスト既存原本")
        assert client.get("/health").json()["document_count"] == 2
