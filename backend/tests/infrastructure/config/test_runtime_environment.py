import os

import pytest
from backend.config import runtime_environment


def test_explicit_environment_wins_and_local_files_supply_defaults(
    tmp_path, monkeypatch
):
    backend = tmp_path / "backend"
    backend.mkdir()
    (backend / ".env.local").write_text(
        "TEST_DB=backend\nTEST_DEFAULT=backend\nTEST_BACKEND_ONLY=ignored\n"
    )
    (tmp_path / ".env.local").write_text("TEST_DB=local\nTEST_DEFAULT=local\n")
    monkeypatch.setattr(runtime_environment, "PROJECT_ROOT", tmp_path)
    monkeypatch.delenv("PYTHON_DOTENV_DISABLED", raising=False)
    monkeypatch.delenv("TEST_DEFAULT", raising=False)
    monkeypatch.delenv("TEST_BACKEND_ONLY", raising=False)
    monkeypatch.setenv("TEST_DB", "explicit")
    runtime_environment.load_runtime_environment()
    assert os.environ["TEST_DB"] == "explicit"
    assert os.environ["TEST_DEFAULT"] == "local"
    assert "TEST_BACKEND_ONLY" not in os.environ
    runtime_environment.load_runtime_environment()
    assert os.environ["TEST_DB"] == "explicit"


def test_disabled_dotenv_does_not_load_local_files(tmp_path, monkeypatch):
    (tmp_path / ".env.local").write_text("TEST_DEFAULT=local\n")
    monkeypatch.setattr(runtime_environment, "PROJECT_ROOT", tmp_path)
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    monkeypatch.delenv("TEST_DEFAULT", raising=False)
    runtime_environment.load_runtime_environment()
    assert "TEST_DEFAULT" not in os.environ


@pytest.mark.parametrize("process_root", [None, "process-root"])
def test_interpolation_uses_root_file_and_process_precedence(
    tmp_path, monkeypatch, process_root
):
    backend = tmp_path / "backend"
    backend.mkdir()
    (tmp_path / ".env").write_text("TEST_IGNORED=base-root\n")
    (backend / ".env.local").write_text("TEST_ROOT=local-root\n")
    (tmp_path / ".env.local").write_text(
        "TEST_ROOT=local-root\n"
        "TEST_INDEX=${TEST_ROOT}/index.sqlite3\n"
        "TEST_NESTED=${TEST_INDEX}/child\n"
        "TEST_FALLBACK=${TEST_UNDEFINED:-fallback}\n"
    )
    monkeypatch.setattr(runtime_environment, "PROJECT_ROOT", tmp_path)
    for name in (
        "PYTHON_DOTENV_DISABLED",
        "TEST_ROOT",
        "TEST_INDEX",
        "TEST_NESTED",
        "TEST_FALLBACK",
        "TEST_UNDEFINED",
    ):
        monkeypatch.delenv(name, raising=False)
    if process_root is not None:
        monkeypatch.setenv("TEST_ROOT", process_root)

    runtime_environment.load_runtime_environment()

    expected_root = process_root or "local-root"
    assert os.environ["TEST_ROOT"] == expected_root
    assert os.environ["TEST_INDEX"] == f"{expected_root}/index.sqlite3"
    assert os.environ["TEST_NESTED"] == f"{expected_root}/index.sqlite3/child"
    assert os.environ["TEST_FALLBACK"] == "fallback"
