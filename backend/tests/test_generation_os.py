import hashlib
import json
import socket
import sqlite3
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from backend.domain.attachment.identifiers import DocumentId
from backend.tests.generation_os_server import main_server
from backend.tests.test_active_attachment_projection import mixed_source
from backend.tests.test_registration_publisher import publish, source
from backend.tests.test_registration_publisher import publisher as publisher


def test_tc099_two_actual_main_processes_refresh_candidates_and_restart_get(publisher):
    first = publish(publisher, source("旧本文"))
    structured = publisher.store.root.parent / "structured"
    structured.mkdir()
    with (
        main_server(publisher.index_path, publisher.store.root, structured) as (
            one,
            p1,
            _,
        ),
        main_server(publisher.index_path, publisher.store.root, structured) as (
            two,
            p2,
            _,
        ),
    ):
        assert p1.pid != p2.pid
        assert one.get("/api/medicines").json()["generation_id"] == first.generation_id
        assert two.get("/api/medicines").json()["generation_id"] == first.generation_id
        replacement = source("新版本文", revised_at="2026-11").replace(
            "製品A".encode(), "新版製品".encode()
        )
        response = one.post(
            "/api/attachment-imports",
            files={"file": ("replacement.xml", replacement, "application/xml")},
        )
        assert response.status_code == 201, response.text
        final = response.json()
        for client in (one, two):
            assert (
                client.get("/health").json()["generation_id"] == final["generation_id"]
            )
            grouped = client.get("/api/medicines").json()
            assert grouped["generation_id"] == final["generation_id"]
            assert grouped["items"][0]["brand_names"] == ["新版製品"]
            assert (
                client.get("/api/medicines/autocomplete").json()["items"][0]["n"]
                == "新版製品"
            )
    with main_server(publisher.index_path, publisher.store.root, structured) as (
        client,
        _,
        _,
    ):
        current = client.get(
            f"/api/attachment-imports/{final['document_id']}/{final['source_sha256']}"
        )
        assert current.status_code == 200
        assert current.json()["generation_id"] == final["generation_id"]
        assert (
            client.get(
                f"/api/attachment-imports/{first.document_id}/{first.source_sha256}"
            ).status_code
            == 410
        )


@pytest.mark.parametrize("component", ["table", "reference", "metadata"])
def test_tc116_individual_published_mutation_refuses_actual_main(publisher, component):
    value = (
        mixed_source()
        .replace(b"<Warnings>", b'<Warnings id="warnings-target">')
        .replace(
            b"</Warnings>",
            b'<Detail><Lang><HeaderRef ref="warnings-target"/></Lang></Detail></Warnings>',
        )
    )
    registered = publish(publisher, value)
    target = publisher.store._target(
        DocumentId(registered.document_id), registered.source_sha256
    )
    # Isolated mutation of an attested active artifact; immutable source stays byte-identical.
    if component == "metadata":
        path = target / "source_metadata.json"
        path.write_bytes(path.read_bytes() + b" ")
    else:
        from pathlib import Path

        with sqlite3.connect(publisher.index_path) as connection:
            manifest = json.loads(
                connection.execute(
                    "SELECT files_json FROM registration_generations WHERE generation_id=?",
                    (registered.generation_id,),
                ).fetchone()[0]
            )
        assert len(manifest) == 1
        path = Path(manifest[0]["path"])
        payload = [
            json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
        ]

        def mutate(node):
            if isinstance(node, dict):
                if (
                    component == "table"
                    and node.get("text") == "A値"
                    and "colspan" in node
                ):
                    node["text"] = "独立表cell改変"
                    return True
                if (
                    component == "reference"
                    and node.get("target_xml_id") == "warnings-target"
                ):
                    node["target_xml_id"] = "independent-changed-target"
                    return True
                return any(mutate(child) for child in node.values())
            if isinstance(node, list):
                return any(mutate(child) for child in node)
            return False

        assert mutate(payload), f"independent {component} field is absent"
        path.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in payload),
            encoding="utf-8",
        )
    assert (target / "source.xml").read_bytes() == value
    structured = publisher.store.root.parent / "structured"
    structured.mkdir()
    with main_server(publisher.index_path, publisher.store.root, structured) as (
        _,
        process,
        log,
    ):
        assert process.poll() is not None
        assert process.returncode != 0
        text = log.read_text(encoding="utf-8")
        assert "Published artifact content differs" in text


@pytest.mark.parametrize("phase", ["artifacts", "commit", "after_commit", "cleanup"])
def test_tc097_113_os_death_reclaims_only_unpublished_owned_attempt(
    publisher, phase, tmp_path
):
    import os
    from pathlib import Path

    from backend.domain.attachment.identifiers import DocumentId

    initial = publish(publisher, source("旧公開本文"))
    value = source("停止対象本文", revised_at="2026-11")
    xml = tmp_path / "new.xml"
    xml.write_bytes(value)
    ready = tmp_path / "stopped.ready"
    environment = os.environ.copy()
    environment["PYTHON_DOTENV_DISABLED"] = "1"
    for key in (
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "ANTHROPIC_API_KEY",
        "TYPESAFE_API_KEY",
    ):
        environment[key] = ""
    structured = publisher.store.root.parent / "structured"
    structured.mkdir()
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    child = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "backend.tests.registration_crash_server",
            "--index",
            str(publisher.index_path),
            "--imports",
            str(publisher.store.root),
            "--structured",
            str(structured),
            "--ready",
            str(ready),
            "--phase",
            phase,
            "--port",
            str(port),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env=environment,
    )
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            assert child.poll() is None
            try:
                if httpx.get(f"http://127.0.0.1:{port}/health").status_code == 200:
                    break
            except httpx.TransportError:
                pass
            time.sleep(0.02)
        with ThreadPoolExecutor(max_workers=1) as requests:
            request = requests.submit(
                httpx.post,
                f"http://127.0.0.1:{port}/api/attachment-imports",
                files={"file": ("stop.xml", value, "application/xml")},
                timeout=20,
            )
            deadline = time.monotonic() + 15
            while not ready.exists() and time.monotonic() < deadline:
                assert child.poll() is None
                time.sleep(0.02)
            assert ready.read_text() == phase
            child.terminate()
            child.wait(timeout=10)
            with pytest.raises(httpx.TransportError):
                request.result(timeout=5)
    finally:
        if child.poll() is None:
            child.terminate()
        child.wait(timeout=10)
    sentinel = publisher.store.root / ".stage-unowned"
    sentinel.mkdir()
    (sentinel / "keep.txt").write_bytes(b"unowned")
    try:
        publisher.recover()
    except sqlite3.OperationalError as exc:
        raise AssertionError(
            f"SQLite process recovery: {exc.sqlite_errorcode} {exc.sqlite_errorname}"
        ) from exc
    target = publisher.store._target(
        DocumentId(initial.document_id), hashlib.sha256(value).hexdigest()
    )
    assert (target / "source.xml").exists() == (phase in {"after_commit", "cleanup"})
    with sqlite3.connect(publisher.index_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM registration_receipts"
        ).fetchone() == ((2,) if phase in {"after_commit", "cleanup"} else (1,))
        assert connection.execute(
            "SELECT COUNT(*) FROM registration_generations"
        ).fetchone() == (1,)
        (body,) = connection.execute("SELECT payload_json FROM units").fetchone()
        assert ("停止対象本文" in body) == (phase in {"after_commit", "cleanup"})
        assert ("旧公開本文" in body) == (phase in {"artifacts", "commit"})
    assert (sentinel / "keep.txt").read_bytes() == b"unowned"
    with main_server(publisher.index_path, publisher.store.root, structured) as (
        client,
        process,
        _,
    ):
        assert process.poll() is None
        assert client.get("/health").json()["unit_count"] == 1


def test_tc116_actual_shared_active_figure_mutation_refuses_main(publisher):
    from backend.infrastructure.persistence.registration_publisher import (
        RegistrationInput,
    )
    from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder

    shared = publisher.store.root / "shared.svg"
    shared.write_bytes(b"<svg>shared active figure</svg>")
    values = (
        source("O共有図本文", ("111111111111", "222222222222")),
        source("Q共有図本文", ("333333333333",), doc="Q"),
    )
    inputs = []
    for name, value in zip(("O", "Q"), values, strict=True):
        path = publisher.store.root / (name + ".xml")
        path.write_bytes(value)
        inputs.append(
            RegistrationInput(
                PmdaXmlDecoder().decode(value), value, (path, shared), path
            )
        )
    publisher.publish_inputs(tuple(inputs), initial=True)
    publish(publisher, source("A新版", revised_at="2026-11"))
    publish(publisher, source("B新版", ("222222222222",), revised_at="2026-11"))
    assert shared.read_bytes() == b"<svg>shared active figure</svg>"
    shared.write_bytes(b"<svg>changed active figure</svg>")
    structured = publisher.store.root.parent / "structured"
    structured.mkdir()
    with main_server(publisher.index_path, publisher.store.root, structured) as (
        _,
        process,
        log,
    ):
        assert process.poll() is not None and process.returncode != 0
        assert "Published artifact content differs" in log.read_text(encoding="utf-8")
