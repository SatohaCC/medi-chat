"""アプリ・CLI・Alembicで共有するDB設定の契約。"""

import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import URL, make_url

from ..project_paths import PROJECT_ROOT

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DatabaseSettings:
    """解決済みの構造化データ・索引パスと接続URL。"""

    structured_dir: Path
    index_path: Path
    database_url: str


def resolve_database_settings(
    *,
    structured_dir: Path | None = None,
    index_path: Path | None = None,
    database_url: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> DatabaseSettings:
    """明示指定、環境設定、構造化データ配下の既定値の順で解決する。"""
    environment = os.environ if environ is None else environ
    source_dir = _resolve_structured_dir(structured_dir, environment)
    if index_path is None and database_url is None:
        environment_path = environment.get("MEDI_CHAT_INDEX_PATH")
        index_path = Path(environment_path) if environment_path is not None else None
        database_url = environment.get("MEDI_CHAT_DATABASE_URL")

    url_path = None
    if database_url is not None:
        parsed_url = make_url(database_url)
        backend_name = parsed_url.get_backend_name()
        if backend_name != "sqlite":
            raise ValueError(
                f"Unsupported database backend {backend_name}: only SQLite is supported"
            )
        url_path = Path(parsed_url.database or "").resolve()
    if index_path is not None:
        database_path = index_path.resolve()
        if url_path is not None and url_path != database_path:
            raise ValueError(
                f"Conflicting database URL and index path: {url_path} != {database_path}"
            )
    elif url_path is not None:
        database_path = url_path
    else:
        database_path = source_dir / ".chat-search.sqlite3"

    resolved_url = URL.create("sqlite", database=database_path.as_posix())
    settings = DatabaseSettings(
        structured_dir=source_dir,
        index_path=database_path,
        database_url=resolved_url.render_as_string(hide_password=False),
    )
    logger.info("Selected SQLite index: %s", settings.index_path)
    return settings


def _resolve_structured_dir(
    structured_dir: Path | None, environ: Mapping[str, str]
) -> Path:
    if structured_dir is not None:
        return structured_dir.resolve()
    environment_dir = environ.get("MEDI_CHAT_STRUCTURED_DIR")
    if environment_dir is not None:
        return Path(environment_dir).resolve()
    candidates = [
        PROJECT_ROOT / "data_tools" / "structured",
        PROJECT_ROOT / "structured",
    ]
    default_dir = next((path for path in candidates if path.exists()), candidates[0])
    return default_dir.resolve()
