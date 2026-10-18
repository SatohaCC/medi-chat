import os

from backend.config import runtime_environment


def test_explicit_environment_wins_and_local_files_supply_defaults(
    tmp_path, monkeypatch
):
    backend = tmp_path / "backend"
    backend.mkdir()
    (backend / ".env.local").write_text("TEST_DB=backend\nTEST_DEFAULT=backend\n")
    (tmp_path / ".env.local").write_text("TEST_DB=local\nTEST_DEFAULT=local\n")
    monkeypatch.setattr(runtime_environment, "BACKEND_DIR", backend)
    monkeypatch.setattr(runtime_environment, "PROJECT_ROOT", tmp_path)
    monkeypatch.delenv("PYTHON_DOTENV_DISABLED", raising=False)
    monkeypatch.delenv("TEST_DEFAULT", raising=False)
    monkeypatch.setenv("TEST_DB", "explicit")
    runtime_environment.load_runtime_environment()
    assert os.environ["TEST_DB"] == "explicit"
    assert os.environ["TEST_DEFAULT"] == "local"
    runtime_environment.load_runtime_environment()
    assert os.environ["TEST_DB"] == "explicit"


def test_disabled_dotenv_does_not_load_local_files(tmp_path, monkeypatch):
    (tmp_path / ".env.local").write_text("TEST_DEFAULT=local\n")
    monkeypatch.setattr(runtime_environment, "BACKEND_DIR", tmp_path)
    monkeypatch.setattr(runtime_environment, "PROJECT_ROOT", tmp_path)
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    monkeypatch.delenv("TEST_DEFAULT", raising=False)
    runtime_environment.load_runtime_environment()
    assert "TEST_DEFAULT" not in os.environ
