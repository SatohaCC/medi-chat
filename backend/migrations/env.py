"""Alembicの追加引数を共通DB設定へ渡す実行環境。"""

from pathlib import Path

from alembic import context

from backend.config.database_settings import resolve_database_settings
from backend.migrations.migration_runner import run_migrations


def run_migration_environment() -> None:
    arguments = context.get_x_argument(as_dictionary=True)
    structured_dir = arguments.get("structured_dir")
    index_path = arguments.get("index_path")
    settings = resolve_database_settings(
        structured_dir=Path(structured_dir) if structured_dir is not None else None,
        index_path=Path(index_path) if index_path is not None else None,
        database_url=arguments.get("database_url"),
    )
    run_migrations(settings)


run_migration_environment()
