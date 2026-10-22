"""HTTP registration keeps originals outside the configured structured directory."""

import os

from backend.infrastructure.persistence.registration_models import (
    PostgresRegistrationInput as RegistrationInput,
)
from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder
from backend.tests.integration.test_postgres_registration import (
    pg_publisher as pg_publisher,
)
from backend.tests.support.postgres_fixtures import pg_engines as pg_engines
from backend.tests.support.registration_oracles import source
from fastapi.testclient import TestClient


def test_http_import_preserves_separately_located_initial_original(
    tmp_path, monkeypatch, pg_engines, pg_publisher
):
    from backend.main import create_app

    originals = tmp_path / "originals"
    originals.mkdir()
    original = originals / "initial.xml"
    original.write_bytes(source("テスト既存原本"))
    pg_publisher.publish_inputs(
        (
            RegistrationInput(
                PmdaXmlDecoder().decode(original.read_bytes()),
                original.read_bytes(),
            ),
        ),
        initial=True,
    )
    monkeypatch.setenv("MEDI_CHAT_ORIGINALS_DIR", str(originals))
    app = create_app(
        database_url=os.environ["TEST_RUNTIME_DATABASE_URL"],
        _database_schema=pg_engines[2],
    )
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


def test_structure_cli_register_preserves_separately_located_initial_original(
    tmp_path, monkeypatch, pg_engines, pg_publisher
):
    from backend.infrastructure.cli.structure_pmda_xml import main as structure_main

    originals = tmp_path / "separate_originals"
    originals.mkdir()
    original = originals / "initial.xml"
    original.write_bytes(source("初期原本"))
    pg_publisher.publish_inputs(
        (
            RegistrationInput(
                PmdaXmlDecoder().decode(original.read_bytes()),
                original.read_bytes(),
            ),
        ),
        initial=True,
    )

    new_xml = tmp_path / "new_incoming.xml"
    new_xml.write_bytes(source("追加原本", ("333333333333",), doc="doc333"))

    monkeypatch.setenv("MEDI_CHAT_ORIGINALS_DIR", str(originals))
    monkeypatch.setattr(
        "sys.argv",
        [
            "structure_pmda_xml",
            "--register",
            "--database-env",
            "TEST_RUNTIME_DATABASE_URL",
            "--schema",
            pg_engines[2],
            str(new_xml),
        ],
    )
    assert structure_main() == 0
    assert original.read_bytes() == source("初期原本")
