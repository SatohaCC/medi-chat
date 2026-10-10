"""相対設定が起動ディレクトリによらず同じデータを選択する。"""

from pathlib import Path

import pytest
from backend.config.database_settings import resolve_database_settings
from sqlalchemy.engine import make_url


@pytest.mark.parametrize("via_environment", [False, True])
@pytest.mark.parametrize("via_url", [False, True])
def test_relative_database_settings_use_project_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    via_environment: bool,
    via_url: bool,
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.setattr("backend.project_paths.PROJECT_ROOT", root)
    environment = (
        {
            "MEDI_CHAT_STRUCTURED_DIR": "data_tools/structured",
            ("MEDI_CHAT_DATABASE_URL" if via_url else "MEDI_CHAT_INDEX_PATH"): (
                "sqlite:///cache/search.sqlite3" if via_url else "cache/search.sqlite3"
            ),
        }
        if via_environment
        else {}
    )
    for cwd in (root, elsewhere):
        monkeypatch.chdir(cwd)
        settings = resolve_database_settings(
            structured_dir=None if via_environment else Path("data_tools/structured"),
            index_path=(
                None if via_environment or via_url else Path("cache/search.sqlite3")
            ),
            database_url=(
                "sqlite:///cache/search.sqlite3"
                if via_url and not via_environment
                else None
            ),
            environ=environment,
        )
        assert settings.structured_dir == root / "data_tools/structured"
        assert settings.index_path == root / "cache/search.sqlite3"
        assert (
            make_url(settings.database_url).database
            == (root / "cache/search.sqlite3").as_posix()
        )
    assert not (elsewhere / "cache").exists()
