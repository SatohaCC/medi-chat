import hashlib
import socket
import sqlite3
import subprocess
import sys
import time
from urllib.request import urlopen

import pytest
from backend.config.database_settings import resolve_database_settings
from backend.config.runtime_environment import load_runtime_environment
from backend.infrastructure.cli.configured_e2e_gate import run_gate, selected_settings
from backend.project_paths import PROJECT_ROOT
from backend.tests.attachment_import_e2e_server import prepare_root


@pytest.mark.parametrize("condition", ["unmanaged", "missing_table"])
def test_unprepared_configured_database_is_not_repaired(tmp_path, condition):
    source, index = prepare_root(tmp_path)
    with sqlite3.connect(index) as connection:
        connection.execute(
            "DROP TABLE alembic_version"
            if condition == "unmanaged"
            else "DROP TABLE units"
        )
    before = index.read_bytes()
    with pytest.raises(RuntimeError, match="unmanaged|missing required tables"):
        run_gate(resolve_database_settings(structured_dir=source, index_path=index))
    assert index.read_bytes() == before


def test_normal_runtime_loading_and_gate_resolve_same_absolute_paths_from_other_cwd(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    load_runtime_environment()
    normal = resolve_database_settings()
    assert selected_settings() == normal
    assert normal.structured_dir.is_absolute() and normal.index_path.is_absolute()
    for environ in [
        {"MEDI_CHAT_STRUCTURED_DIR": "data/pmda/structured"},
        {"MEDI_CHAT_INDEX_PATH": "tmp/explicit.sqlite3"},
        {"MEDI_CHAT_DATABASE_URL": "sqlite:///tmp/explicit.sqlite3"},
    ]:
        with monkeypatch.context() as configured:
            for name in [
                "MEDI_CHAT_STRUCTURED_DIR",
                "MEDI_CHAT_INDEX_PATH",
                "MEDI_CHAT_DATABASE_URL",
            ]:
                configured.delenv(name, raising=False)
            for name, value in environ.items():
                configured.setenv(name, value)
            resolved = resolve_database_settings()
            assert selected_settings() == resolved
            if "MEDI_CHAT_STRUCTURED_DIR" in environ:
                assert resolved.structured_dir == PROJECT_ROOT / "data/pmda/structured"
            else:
                assert resolved.index_path == PROJECT_ROOT / "tmp/explicit.sqlite3"


def test_failed_os_health_stops_only_the_spawned_process(tmp_path, monkeypatch):
    source, index = prepare_root(tmp_path)
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 3215))
    original = subprocess.Popen
    owned = []

    def spawn_unhealthy(_command, **kwargs):
        if _command[0] == "taskkill":
            return original(_command, **kwargs)
        child = original(
            [sys.executable, "-m", "http.server", "3215", "--bind", "127.0.0.1"],
            **kwargs,
        )
        owned.append(child)
        return child

    monkeypatch.setattr(subprocess, "Popen", spawn_unhealthy)
    with pytest.raises(RuntimeError, match="health timed out"):
        run_gate(
            resolve_database_settings(structured_dir=source, index_path=index),
            port=3215,
            timeout=0.5,
        )
    assert len(owned) == 1 and owned[0].poll() is not None
    with socket.socket() as stopped:
        assert stopped.connect_ex(("127.0.0.1", 3215)) != 0
    print(f"failed_health_owned_pid={owned[0].pid} port=3215 terminated=true")


def test_real_sentinel_process_survives_occupied_probe(tmp_path):
    source, index = prepare_root(tmp_path)
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 3214))
    sentinel = subprocess.Popen(
        [sys.executable, "-m", "http.server", "3214", "--bind", "127.0.0.1"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(50):
            try:
                with urlopen("http://127.0.0.1:3214", timeout=1) as response:
                    assert response.status == 200
                break
            except OSError:
                time.sleep(0.1)
        else:
            pytest.fail("Owned sentinel did not start")
        with pytest.raises(RuntimeError, match="occupied"):
            run_gate(
                resolve_database_settings(structured_dir=source, index_path=index),
                port=3214,
            )
        assert sentinel.poll() is None
        print(f"sentinel_pid={sentinel.pid} occupied_port=3214 survived=true")
    finally:
        sentinel.terminate()
        sentinel.wait(timeout=10)


def test_missing_configured_index_fails_without_creating_it(tmp_path):
    settings = resolve_database_settings(
        structured_dir=tmp_path, index_path=tmp_path / "absent.sqlite3"
    )
    with pytest.raises(RuntimeError, match="does not exist"):
        run_gate(settings)
    assert not settings.index_path.exists()


def test_configured_stale_is_not_replaced_by_fresh_success(tmp_path):
    source, index = prepare_root(tmp_path)
    before = hashlib.sha256(index.read_bytes()).hexdigest()
    unit = next(source.rglob("search_units.jsonl"))
    unit.write_bytes(unit.read_bytes() + b"\n")
    with pytest.raises(RuntimeError, match="Published artifact content differs"):
        run_gate(resolve_database_settings(structured_dir=source, index_path=index))
    assert hashlib.sha256(index.read_bytes()).hexdigest() == before


def test_occupied_port_is_not_taken_over(tmp_path):
    source, index = prepare_root(tmp_path)
    with socket.socket() as sentinel:
        sentinel.bind(("127.0.0.1", 0))
        sentinel.listen()
        port = sentinel.getsockname()[1]
        with pytest.raises(RuntimeError, match="occupied"):
            run_gate(
                resolve_database_settings(structured_dir=source, index_path=index),
                port=port,
            )
        assert sentinel.getsockname()[1] == port
