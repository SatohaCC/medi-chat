"""Explicit registration preparation; existing JSON/XML bytes are never rewritten."""

import json
import shutil
from pathlib import Path

from backend.infrastructure.persistence.attachment_import_store import (
    FileAttachmentImportStore,
)
from backend.infrastructure.persistence.registration_publisher import (
    RegistrationInput,
    SqliteRegistrationPublisher,
)
from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder
from backend.tests.integration.test_registration_initialization import command
from backend.tests.support.attachment_import_fixtures import xml_source


def register_synthetic_prepared_index(structured: Path, index: Path) -> None:
    document = structured / "test_001" / "document.json"
    units = document.parent / "search_units.jsonl"
    payload = json.loads(document.read_bytes())
    texts = [
        json.loads(line)["text"]
        for line in units.read_text(encoding="utf-8").splitlines()
        if line
    ]
    import html

    raw = xml_source(
        "<AdverseEvents><Detail><Lang>"
        + html.escape(" ".join(texts))
        + "</Lang></Detail></AdverseEvents>"
    )
    raw = (
        raw.replace(b"000001", b"test")
        .replace(
            b"<PackageInsertNo>test</PackageInsertNo>",
            b"<PackageInsertNo>001</PackageInsertNo>",
        )
        .replace(b"111111111111", b"1234567A0000")
        .replace("製品A".encode(), "テスト薬".encode())
    )
    original = index.parent / "originals" / "runtime-original.xml"
    original.parent.mkdir(parents=True, exist_ok=True)
    original.write_bytes(raw)
    publisher = SqliteRegistrationPublisher(
        index,
        FileAttachmentImportStore(index.parent / "imports"),
        allowed_roots=(structured, index.parent / "originals"),
    )
    publisher.publish_inputs(
        (
            RegistrationInput(
                PmdaXmlDecoder().decode(raw),
                raw,
                (original, document, units),
                original,
                payload,
            ),
        ),
        initial=True,
    )


def register_existing_test_source(structured: Path, index: Path) -> Path:
    root = index.parent / "prepared-copy"
    originals = root / "originals"
    copied = root / "structured"
    shutil.copytree(structured.parent / "originals", originals)
    shutil.copytree(structured, copied, ignore=shutil.ignore_patterns("*.sqlite3*"))
    result = command(
        root,
        "backend.infrastructure.cli.initialize_registrations",
        "--originals-dir",
        originals,
        "--structured-dir",
        copied,
        "--index-path",
        index,
        "--import-dir",
        index.parent / "imports",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return copied
