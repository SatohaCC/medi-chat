"""TC045/046/048/049/051/058/072 independent canonical process observations."""

import csv
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from backend.tests.support.paths import PROJECT_ROOT
from backend.tests.support.postgres_fixtures import pg_api as pg_api
from backend.tests.support.postgres_fixtures import pg_engines as pg_engines

ROOT = PROJECT_ROOT


def process(
    code: list[str],
    cwd: Path,
    *,
    schema: str | None = None,
):
    environment = dict(os.environ)
    environment.update(
        PYTHONPATH=str(ROOT),
        PYTHON_DOTENV_DISABLED="1",
        TYPESAFE_API_KEY="",
        JEV_API_KEY="",
        OPENAI_API_KEY="",
        GEMINI_API_KEY="",
        GOOGLE_API_KEY="",
    )
    for key in (
        "MEDI_CHAT_STRUCTURED_DIR",
        "MEDI_CHAT_INDEX_PATH",
        "MEDI_CHAT_IMPORT_DIR",
        "MEDI_CHAT_IMPORT_ROOT",
    ):
        environment.pop(key, None)
    if schema is not None:
        environment["MEDI_CHAT_DATABASE_URL"] = os.environ["TEST_RUNTIME_DATABASE_URL"]
        environment["MEDI_CHAT_DATABASE_SCHEMA"] = schema
    environment["PYTHONUTF8"] = "1"
    return subprocess.run(
        [sys.executable, *code],
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )


def test_canonical_modules_and_existing_api_work_with_legacy_imports_forbidden(
    tmp_path,
    pg_api,
    pg_engines,
):
    code = """
import importlib, importlib.abc, sys
class RejectLegacy(importlib.abc.MetaPathFinder):
    forbidden = ("package_inserts", "data_tools", "backend.chat", "backend.retrieval", "backend.medicines", "backend.storage", "backend.jev", "backend.infrastructure.persistence.sqlite_engine", "backend.infrastructure.persistence.registration_publisher", "backend.infrastructure.persistence.attachment_import_store", "backend.infrastructure.persistence.evidence_reader", "backend.infrastructure.persistence.medicine_reader", "backend.infrastructure.persistence.generation_runtime", "backend.infrastructure.sources.file_index_source")
    def find_spec(self, fullname, path=None, target=None):
        if any(fullname == name or fullname.startswith(name + ".") for name in self.forbidden):
            raise RuntimeError("Legacy dependency attempted: " + fullname)
sys.meta_path.insert(0, RejectLegacy())
for module in ("backend.presentation.chat_service", "backend.infrastructure.cli.manage_postgres", "backend.infrastructure.cli.structure_pmda_xml", "backend.infrastructure.cli.build_autocomplete_index"):
    importlib.import_module(module)
from backend.main import create_app
from fastapi.testclient import TestClient
with TestClient(create_app()) as client:
    assert client.get("/api").json() == {"status": "ok"}
    assert client.get("/health").json()["status"] == "ok"
    assert len(client.get("/api/medicines").json()["items"]) == 1
    response = client.post("/api/chat", json={"message": "頭痛", "product_yj_codes": ["999999999999"]})
    assert response.status_code == 200 and response.json()["needs_clarification"]
    with client.websocket_connect("/api/ws") as socket:
        socket.send_json({"type": "ping"})
        assert socket.receive_json() == {"type": "pong"}
assert not any(any(name == old or name.startswith(old + ".") for old in RejectLegacy.forbidden) for name in sys.modules)
print("canonical independent API passed")
"""
    result = process(["-c", code], tmp_path, schema=pg_engines[2])
    assert result.returncode == 0, result.stdout + result.stderr
    assert "canonical independent API passed" in result.stdout


@pytest.mark.parametrize("batch", [False, True])
@pytest.mark.parametrize("missing", [False, True])
def test_xml_module_entrypoint_is_strict_in_single_and_batch_modes(
    tmp_path, batch, missing
):
    original = next((ROOT / "data/pmda/originals").glob("*/*630004*.xml"))
    source_dir = tmp_path / "originals"
    shutil.copytree(original.parent, source_dir)
    source = source_dir / original.name
    if missing:
        next(source_dir.glob("*.gif")).unlink()
    output = tmp_path / "generated"
    inputs = ["--source-dir", str(source_dir)] if batch else [str(source)]
    result = process(
        [
            "-m",
            "backend.infrastructure.cli.structure_pmda_xml",
            *inputs,
            "--output-dir",
            str(output),
        ],
        tmp_path,
    )
    assert result.returncode == int(missing), result.stdout + result.stderr
    assert bool(list(output.rglob("document.json"))) is not missing


def test_index_module_entrypoint_uses_explicit_postgres_schema(
    tmp_path, pg_api, pg_engines
):
    result = process(
        [
            "-m",
            "backend.infrastructure.cli.manage_postgres",
            "--database-env",
            "TEST_RUNTIME_DATABASE_URL",
            "--schema",
            pg_engines[2],
            "rebuild",
            "--confirm-schema",
            pg_engines[2],
        ],
        tmp_path,
        schema=pg_engines[2],
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["retained_versions"] == 1


def test_autocomplete_module_keeps_cp932_active_rows_and_compact_contract(tmp_path):
    source = tmp_path / "sample.csv"
    active = [""] * 38
    active[4] = "ガスター散２％"
    active[6] = "ｶﾞｽﾀｰｻﾝ2%"
    active[27] = "1"
    active[30] = "99999999"
    active[31] = "2325003B2029"
    active[37] = "【般】ファモチジン散２％"
    expired = active.copy()
    expired[4] = "期限切薬品"
    expired[30] = "20220331"
    with source.open("w", encoding="cp932", newline="") as stream:
        csv.writer(stream).writerows([active, active, expired, ["incomplete"]])
    output = tmp_path / "dictionary.json"
    result = process(
        [
            "-m",
            "backend.infrastructure.cli.build_autocomplete_index",
            "--csv-path",
            str(source),
            "--output",
            str(output),
        ],
        tmp_path,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(output.read_text(encoding="utf-8")) == [
        {
            "n": "ガスター散２％",
            "k": "ガスターサン2%",
            "h": "がすたーさん2%",
            "y": "2325003B2029",
            "g": "ファモチジン散２％",
            "c": "内用",
        }
    ]
