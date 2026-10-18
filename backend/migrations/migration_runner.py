"""解決済みDB設定を受け取るmigration実行境界。"""

from collections.abc import MutableMapping
from typing import Literal

from alembic import context
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

from ..config.database_settings import DatabaseSettings
from ..infrastructure.persistence.registration_schema import (
    TABLES as REGISTRATION_TABLES,
)
from ..infrastructure.persistence.schema import metadata
from ..infrastructure.persistence.sqlite_engine import create_sqlite_engine


def _include_schema_name(
    name: str | None,
    type_: str,
    parent_names: MutableMapping[
        Literal["schema_name", "table_name", "schema_qualified_table_name"], str | None
    ],
) -> bool:
    """手管理のFTS本体とSQLite shadow tableはautogenerateから除外する。"""
    if type_ == "table" and name is not None:
        return name != "unit_fts" and not name.startswith("unit_fts_")
    return True


def _validate_managed_database(connection: Connection) -> None:
    """空DBまたは既知の管理状態だけをDDL前に受理する。"""
    table_names = inspect(connection).get_table_names()
    if table_names and "alembic_version" not in table_names:
        raise ValueError(
            f"Unmanaged database schema contains existing tables: {', '.join(table_names)}"
        )
    revisions = MigrationContext.configure(connection).get_current_heads()
    scripts = ScriptDirectory.from_config(context.config)
    for revision in revisions:
        scripts.get_revision(revision)
    if revisions and set(revisions) != set(scripts.get_heads()):
        raise ValueError(
            "Unsupported database revision; create a new database and register original sources"
        )

    expected_objects = {("table", "alembic_version")} if table_names else set()
    if revisions:
        registration_names = {table.name for table in REGISTRATION_TABLES}
        selected_tables = [
            table
            for table in metadata.tables.values()
            if table.name not in registration_names
            or "0002_registration_generations" in revisions
        ]
        expected_objects.update(("table", table.name) for table in selected_tables)
        expected_objects.update(
            ("index", index.name)
            for table in selected_tables
            for index in table.indexes
            if index.name is not None
        )
        expected_objects.update(
            ("table", name)
            for name in (
                "unit_fts",
                "unit_fts_data",
                "unit_fts_idx",
                "unit_fts_content",
                "unit_fts_docsize",
                "unit_fts_config",
            )
        )
    actual_objects = {
        (object_type, name)
        for object_type, name in connection.execute(
            text(
                "SELECT type, name FROM sqlite_master WHERE substr(name, 1, 7) != 'sqlite_'"
            )
        )
    }
    if actual_objects != expected_objects:
        raise ValueError(
            "Unknown managed database schema: "
            f"unexpected objects {sorted(actual_objects - expected_objects)}, "
            f"missing objects {sorted(expected_objects - actual_objects)}"
        )


def run_migrations(settings: DatabaseSettings) -> None:
    engine = create_sqlite_engine(settings.database_url)
    try:
        with engine.begin() as connection:
            _validate_managed_database(connection)
            context.configure(
                connection=connection,
                target_metadata=metadata,
                include_name=_include_schema_name,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()
