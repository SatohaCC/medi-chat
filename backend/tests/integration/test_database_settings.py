"""共通resolverと実際の三入口によるSQLite設定選択を検証する。"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import pytest
from alembic.config import CommandLine
from backend import main as application_entrypoint
from backend.config import database_settings
from backend.config.database_settings import DatabaseSettings
from backend.infrastructure.cli import build_search_index as index_entrypoint
from backend.migrations import migration_runner
from backend.tests.support.paths import BACKEND_ROOT
from sqlalchemy.engine import make_url


class StopBeforeDatabase(Exception):
    """設定選択の観測後、DB接続・保守処理へ進ませない。"""


@dataclass(frozen=True)
class SelectionInput:
    structured_dir: Path
    index_path: Path | None
    database_url: str | None
    environ: dict[str, str]
    expected_path: Path


def _run_database_entrypoint(
    entrypoint: str,
    *,
    structured_dir: Path | None,
    index_path: Path | None,
    database_url: str | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # These tests observe settings before any DB I/O. Recovery is independently
    # exercised by the startup/crash suites, so keep the existing readiness spy.
    if entrypoint in {"application", "cli"}:
        monkeypatch.setattr(
            application_entrypoint if entrypoint == "application" else index_entrypoint,
            "recover_sqlite_journal",
            lambda selected: None,
        )
    if entrypoint == "application":
        app = application_entrypoint.create_app(
            structured_dir=structured_dir,
            index_path=index_path,
            database_url=database_url,
        )

        async def start_application() -> None:
            async with app.router.lifespan_context(app):
                pytest.fail("設定確認からDB停止hookを通らず起動した")

        asyncio.run(start_application())
    elif entrypoint == "cli":
        argv = ["build_search_index"]
        if structured_dir is not None:
            argv.extend(["--structured-dir", str(structured_dir)])
        if index_path is not None:
            argv.extend(["--index-path", str(index_path)])
        if database_url is not None:
            argv.extend(["--database-url", database_url])
        monkeypatch.setattr("sys.argv", argv)
        index_entrypoint.main()
    elif entrypoint == "alembic":
        ini_path = BACKEND_ROOT / "alembic.ini"
        argv = ["-c", str(ini_path)]
        if structured_dir is not None:
            argv.extend(["-x", f"structured_dir={structured_dir}"])
        if index_path is not None:
            argv.extend(["-x", f"index_path={index_path}"])
        if database_url is not None:
            argv.extend(["-x", f"database_url={database_url}"])
        CommandLine().main(argv=[*argv, "upgrade", "head"])
    else:
        pytest.fail(f"未知の実入口: {entrypoint}")


@pytest.fixture(
    params=[
        "explicit_path",
        "explicit_url",
        "environment_path",
        "environment_url",
        "default",
    ]
)
def selection_input(tmp_path: Path, request: pytest.FixtureRequest) -> SelectionInput:
    source = tmp_path / "structured"
    explicit = tmp_path / "explicit.sqlite3"
    environment_path = tmp_path / "environment-path.sqlite3"
    environment_url_path = tmp_path / "environment-url.sqlite3"
    source.mkdir()
    # 明示指定がある場合だけ、下位の環境URL/pathを異なる先に競合させる。
    lower_conflict = {
        "MEDI_CHAT_INDEX_PATH": str(environment_path),
        "MEDI_CHAT_DATABASE_URL": f"sqlite:///{environment_url_path.as_posix()}",
    }
    choices: dict[str, tuple[Path | None, str | None, dict[str, str], Path]] = {
        "explicit_path": (explicit, None, lower_conflict, explicit),
        "explicit_url": (
            None,
            f"sqlite:///{explicit.as_posix()}",
            lower_conflict,
            explicit,
        ),
        "environment_path": (
            None,
            None,
            {"MEDI_CHAT_INDEX_PATH": str(environment_path)},
            environment_path,
        ),
        "environment_url": (
            None,
            None,
            {"MEDI_CHAT_DATABASE_URL": f"sqlite:///{environment_url_path.as_posix()}"},
            environment_url_path,
        ),
        "default": (None, None, {}, source / ".chat-search.sqlite3"),
    }
    index_path, database_url, environ, expected_path = choices[request.param]
    return SelectionInput(source, index_path, database_url, environ, expected_path)


@pytest.mark.parametrize("entrypoint", ["resolver", "application", "cli", "alembic"])
def test_database_selection_is_shared_by_all_entrypoints(
    selection_input: SelectionInput,
    entrypoint: str,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    case = selection_input
    for key in (
        "MEDI_CHAT_STRUCTURED_DIR",
        "MEDI_CHAT_INDEX_PATH",
        "MEDI_CHAT_DATABASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)
    for key, value in case.environ.items():
        monkeypatch.setenv(key, value)
    caplog.set_level(logging.INFO)

    real_resolver = database_settings.resolve_database_settings
    requests: list[dict[str, object]] = []
    resolved: list[DatabaseSettings] = []
    consumed_paths: list[Path] = []
    migration_settings: list[DatabaseSettings] = []

    def recording_resolver(
        *,
        structured_dir: Path | None = None,
        index_path: Path | None = None,
        database_url: str | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> DatabaseSettings:
        requests.append(
            {
                "structured_dir": structured_dir,
                "index_path": index_path,
                "database_url": database_url,
                "environ": environ,
            }
        )
        settings = real_resolver(
            structured_dir=structured_dir,
            index_path=index_path,
            database_url=database_url,
            environ=environ,
        )
        resolved.append(settings)
        return settings

    def stop_database(index_path: Path) -> None:
        consumed_paths.append(index_path)
        raise StopBeforeDatabase

    def stop_app(structured_dir: Path, index_path: Path) -> None:
        consumed_paths.append(index_path)
        raise StopBeforeDatabase

    def stop_migrations(settings: DatabaseSettings) -> None:
        migration_settings.append(settings)
        consumed_paths.append(settings.index_path)
        raise StopBeforeDatabase

    # 実resolverへ委譲するSpy。実入口が同じresolverを呼ぶことも観測する。
    monkeypatch.setattr(
        database_settings, "resolve_database_settings", recording_resolver
    )
    for module in (application_entrypoint, index_entrypoint):
        monkeypatch.setattr(
            module, "resolve_database_settings", recording_resolver, raising=False
        )
    monkeypatch.setattr(
        application_entrypoint, "verify_index_readiness", stop_app, raising=False
    )
    monkeypatch.setattr(
        index_entrypoint, "verify_schema_readiness", stop_database, raising=False
    )
    monkeypatch.setattr(migration_runner, "run_migrations", stop_migrations)

    arguments = {
        "structured_dir": case.structured_dir,
        "index_path": case.index_path,
        "database_url": case.database_url,
    }
    if entrypoint == "resolver":
        recording_resolver(
            structured_dir=case.structured_dir,
            index_path=case.index_path,
            database_url=case.database_url,
            environ=case.environ,
        )
    else:
        with pytest.raises(StopBeforeDatabase):
            _run_database_entrypoint(
                entrypoint,
                structured_dir=case.structured_dir,
                index_path=case.index_path,
                database_url=case.database_url,
                monkeypatch=monkeypatch,
            )

    assert len(requests) == 1, f"{entrypoint}が共通resolverを一度呼ぶ必要がある"
    for name, expected in arguments.items():
        assert requests[0].get(name) == expected
    assert len(resolved) == 1
    settings = resolved[0]
    assert type(settings) is DatabaseSettings
    assert settings.structured_dir == case.structured_dir
    assert settings.index_path == case.expected_path
    assert settings.index_path.is_absolute()
    if entrypoint != "resolver":
        assert consumed_paths == [case.expected_path]
        captured = capsys.readouterr()
        assert str(case.expected_path) in captured.out + captured.err + caplog.text
    if entrypoint == "alembic":
        assert migration_settings[0] is settings


def _snapshot_files(directory: Path) -> dict[Path, bytes]:
    return {
        path.relative_to(directory): path.read_bytes()
        for path in directory.rglob("*")
        if path.is_file()
    }


@pytest.mark.parametrize("entrypoint", ["application", "cli", "alembic"])
@pytest.mark.parametrize("level", ["explicit", "environment"])
@pytest.mark.parametrize("relation", ["same_file", "different_files"])
def test_conflicting_url_and_path_are_rejected_before_connect(
    tmp_path: Path,
    entrypoint: str,
    level: str,
    relation: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "structured"
    source.mkdir()
    alias_dir = tmp_path / "alias"
    alias_dir.mkdir()
    database_path = tmp_path / "existing.sqlite3"
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("CREATE TABLE preserved (value TEXT NOT NULL)")
        connection.execute("INSERT INTO preserved VALUES ('変更前の値')")
        connection.commit()
    finally:
        connection.close()
    url_path = (
        alias_dir / ".." / database_path.name
        if relation == "same_file"
        else tmp_path / "must-not-be-created.sqlite3"
    )
    database_url = f"sqlite:///{url_path.as_posix()}"
    before = _snapshot_files(tmp_path)
    boundary_calls: list[Path] = []

    def stop_database(index_path: Path) -> None:
        boundary_calls.append(index_path)
        raise StopBeforeDatabase

    def stop_app(structured_dir: Path, index_path: Path) -> None:
        boundary_calls.append(index_path)
        raise StopBeforeDatabase

    def stop_migrations(settings: DatabaseSettings) -> None:
        stop_database(settings.index_path)

    monkeypatch.setattr(
        application_entrypoint, "verify_index_readiness", stop_app, raising=False
    )
    monkeypatch.setattr(
        index_entrypoint, "verify_schema_readiness", stop_database, raising=False
    )
    monkeypatch.setattr(migration_runner, "run_migrations", stop_migrations)
    for key in (
        "MEDI_CHAT_STRUCTURED_DIR",
        "MEDI_CHAT_INDEX_PATH",
        "MEDI_CHAT_DATABASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)
    if level == "environment":
        monkeypatch.setenv("MEDI_CHAT_INDEX_PATH", str(database_path))
        monkeypatch.setenv("MEDI_CHAT_DATABASE_URL", database_url)

    error: Exception | None = None
    try:
        _run_database_entrypoint(
            entrypoint,
            structured_dir=source,
            index_path=database_path if level == "explicit" else None,
            database_url=database_url if level == "explicit" else None,
            monkeypatch=monkeypatch,
        )
    except ImportError, TypeError, NotImplementedError:
        raise
    except Exception as caught:
        error = caught

    # 既存DBの全bytesと存在する全ファイルを比較し、内容変更と新規作成を検出する。
    assert _snapshot_files(tmp_path) == before
    if relation == "same_file":
        assert isinstance(error, StopBeforeDatabase)
        assert boundary_calls == [database_path]
    else:
        assert boundary_calls == [], "異なるURL/pathを拒否する前にDB境界へ到達した"
        assert error is not None
        reason = str(error).lower()
        assert "url" in reason
        assert "path" in reason or "パス" in reason
        assert any(word in reason for word in ("conflict", "different", "競合", "異な"))


@pytest.mark.parametrize("entrypoint", ["resolver", "application", "cli", "alembic"])
@pytest.mark.parametrize(
    "location", ["windows_absolute", "project_relative", "non_sqlite"]
)
def test_supported_database_locations_are_normalized(
    tmp_path: Path,
    entrypoint: str,
    location: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "structured"
    source.mkdir()
    working_dir = tmp_path / "working-dir"
    working_dir.mkdir()
    monkeypatch.chdir(working_dir)
    monkeypatch.setattr("backend.project_paths.PROJECT_ROOT", tmp_path)
    for key in (
        "MEDI_CHAT_STRUCTURED_DIR",
        "MEDI_CHAT_INDEX_PATH",
        "MEDI_CHAT_DATABASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)

    index_path: Path | None = None
    database_url: str | None = None
    expected_path: Path | None = None
    if location == "windows_absolute":
        index_path = tmp_path / "索引 DB.sqlite3"
        # 実Windowsのドライブ付き絶対パスを入力し、skipや擬似Windows値で代替しない。
        assert index_path.drive and "\\" in str(index_path)
        expected_path = tmp_path / "索引 DB.sqlite3"
    elif location == "project_relative":
        index_path = Path("cache") / "相対索引.sqlite3"
        expected_path = tmp_path / "cache" / "相対索引.sqlite3"
    else:
        database_url = "postgresql://db.example.test/unsupported"

    before = _snapshot_files(tmp_path)
    boundary_calls: list[Path] = []

    def stop_database(selected_path: Path) -> None:
        boundary_calls.append(selected_path)
        raise StopBeforeDatabase

    def stop_app(structured_dir: Path, index_path: Path) -> None:
        boundary_calls.append(index_path)
        raise StopBeforeDatabase

    def stop_migrations(settings: DatabaseSettings) -> None:
        stop_database(settings.index_path)

    monkeypatch.setattr(
        application_entrypoint, "verify_index_readiness", stop_app, raising=False
    )
    monkeypatch.setattr(
        index_entrypoint, "verify_schema_readiness", stop_database, raising=False
    )
    monkeypatch.setattr(migration_runner, "run_migrations", stop_migrations)

    settings: DatabaseSettings | None = None
    error: Exception | None = None
    try:
        if entrypoint == "resolver":
            settings = database_settings.resolve_database_settings(
                structured_dir=source,
                index_path=index_path,
                database_url=database_url,
                environ={},
            )
        else:
            _run_database_entrypoint(
                entrypoint,
                structured_dir=source,
                index_path=index_path,
                database_url=database_url,
                monkeypatch=monkeypatch,
            )
    except ImportError, TypeError, NotImplementedError:
        raise
    except Exception as caught:
        error = caught

    assert _snapshot_files(tmp_path) == before
    if location == "non_sqlite":
        assert boundary_calls == [], "非SQLite URLを拒否する前にDB境界へ到達した"
        assert settings is None, "非SQLite URLからSQLite設定を生成して受理した"
        assert error is not None
        reason = str(error).lower()
        assert "postgresql" in reason
        assert "sqlite" in reason
        assert any(
            word in reason
            for word in ("unsupported", "not supported", "未対応", "only", "のみ")
        )
    elif entrypoint == "resolver":
        assert error is None
        assert settings is not None
        assert type(settings) is DatabaseSettings
        assert settings.index_path == expected_path
        assert settings.index_path.is_absolute()
        parsed_url = make_url(settings.database_url)
        assert parsed_url.get_backend_name() == "sqlite"
        assert expected_path is not None
        assert parsed_url.database is not None
        assert parsed_url.database == expected_path.as_posix()
        assert Path(parsed_url.database) == expected_path
    else:
        assert isinstance(error, StopBeforeDatabase)
        assert expected_path is not None and expected_path.is_absolute()
        assert boundary_calls == [expected_path]


@pytest.mark.parametrize("entrypoint", ["application", "cli", "alembic"])
@pytest.mark.parametrize(
    "selection",
    ["explicit", "environment", "both_candidates", "second_candidate", "no_candidate"],
)
def test_structured_directory_resolution_is_shared(
    tmp_path: Path,
    entrypoint: str,
    selection: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = tmp_path / "isolated-project"
    project_root.mkdir()
    first_candidate = project_root / "data" / "pmda" / "structured"
    second_candidate = project_root / "structured"
    explicit_source = tmp_path / "explicit-source"
    environment_source = tmp_path / "environment-source"
    explicit_source.mkdir()
    environment_source.mkdir()
    if selection in ("explicit", "environment", "both_candidates"):
        first_candidate.mkdir(parents=True)
        second_candidate.mkdir()
    elif selection == "second_candidate":
        second_candidate.mkdir()
    expected_sources = {
        "explicit": explicit_source,
        "environment": environment_source,
        "both_candidates": first_candidate,
        "second_candidate": second_candidate,
        "no_candidate": first_candidate,
    }
    expected_source = expected_sources[selection]
    monkeypatch.setattr(database_settings, "PROJECT_ROOT", project_root)
    for key in (
        "MEDI_CHAT_STRUCTURED_DIR",
        "MEDI_CHAT_INDEX_PATH",
        "MEDI_CHAT_DATABASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)
    if selection in ("explicit", "environment"):
        monkeypatch.setenv("MEDI_CHAT_STRUCTURED_DIR", str(environment_source))

    consumed: list[tuple[Path, Path]] = []
    recorded_settings: list[DatabaseSettings] = []
    real_resolver = database_settings.resolve_database_settings

    def recording_resolver(
        *,
        structured_dir: Path | None = None,
        index_path: Path | None = None,
        database_url: str | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> DatabaseSettings:
        res = real_resolver(
            structured_dir=structured_dir,
            index_path=index_path,
            database_url=database_url,
            environ=environ,
        )
        recorded_settings.append(res)
        return res

    monkeypatch.setattr(
        database_settings, "resolve_database_settings", recording_resolver
    )
    for module in (application_entrypoint, index_entrypoint):
        monkeypatch.setattr(
            module, "resolve_database_settings", recording_resolver, raising=False
        )

    def stop_app(source_dir: Path, index_path: Path) -> None:
        consumed.append((source_dir, index_path))
        raise StopBeforeDatabase

    def stop_cli(index_path: Path) -> None:
        consumed.append((recorded_settings[-1].structured_dir, index_path))
        raise StopBeforeDatabase

    def stop_migrations(settings: DatabaseSettings) -> None:
        consumed.append((settings.structured_dir, settings.index_path))
        raise StopBeforeDatabase

    monkeypatch.setattr(
        application_entrypoint, "verify_index_readiness", stop_app, raising=False
    )
    monkeypatch.setattr(
        index_entrypoint, "verify_schema_readiness", stop_cli, raising=False
    )
    monkeypatch.setattr(migration_runner, "run_migrations", stop_migrations)

    with pytest.raises(StopBeforeDatabase):
        _run_database_entrypoint(
            entrypoint,
            structured_dir=explicit_source if selection == "explicit" else None,
            index_path=None,
            database_url=None,
            monkeypatch=monkeypatch,
        )

    assert expected_source.is_absolute()
    assert consumed == [(expected_source, expected_source / ".chat-search.sqlite3")]
    if selection == "no_candidate":
        assert not first_candidate.exists()
        assert not second_candidate.exists()
