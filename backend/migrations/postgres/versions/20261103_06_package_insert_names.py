"""Rename persisted attachment tables to their package-insert names."""

from alembic import op
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

revision = "pg_20261103_06"
down_revision = "pg_20261024_05"
branch_labels = None
depends_on = None

_TABLE_RENAMES = (
    ("attachment_versions", "package_insert_versions"),
    ("attachment_assets", "package_insert_assets"),
    ("attachment_uploads", "package_insert_uploads"),
    ("attachment_upload_parts", "package_insert_upload_parts"),
)
_EXPIRY_INDEX = (
    "ix_attachment_uploads_expires_at",
    "ix_package_insert_uploads_expires_at",
)


def _schema_name(connection: Connection) -> str:
    schema = connection.execute(text("SELECT current_schema()")).scalar_one_or_none()
    if not isinstance(schema, str):
        raise RuntimeError("Could not resolve the current PostgreSQL schema")
    return schema


def _rename_tables(renames: tuple[tuple[str, str], ...]) -> None:
    connection = op.get_bind()
    schema = _schema_name(connection)
    tables = set(inspect(connection).get_table_names(schema=schema))
    for old_name, new_name in renames:
        old_exists = old_name in tables
        new_exists = new_name in tables
        if old_exists == new_exists:
            if old_exists:
                raise RuntimeError(
                    f"Refusing ambiguous table rename: both {old_name} and {new_name} exist"
                )
            raise RuntimeError(
                f"Refusing table rename: neither {old_name} nor {new_name} exists"
            )
        if old_exists:
            op.rename_table(old_name, new_name, schema=schema)
            tables.remove(old_name)
            tables.add(new_name)


def _rename_expiry_index(old_name: str, new_name: str) -> None:
    connection = op.get_bind()
    schema = _schema_name(connection)
    indexes = {
        item["name"]
        for item in inspect(connection).get_indexes(
            "package_insert_uploads"
            if new_name == _EXPIRY_INDEX[1]
            else "attachment_uploads",
            schema=schema,
        )
    }
    if old_name in indexes and new_name not in indexes:
        preparer = connection.dialect.identifier_preparer
        qualified_old = f"{preparer.quote_schema(schema)}.{preparer.quote(old_name)}"
        op.execute(
            text(f"ALTER INDEX {qualified_old} RENAME TO {preparer.quote(new_name)}")
        )
    elif old_name in indexes or new_name not in indexes:
        raise RuntimeError(
            f"Refusing ambiguous index rename: expected {old_name} or {new_name}"
        )


def upgrade() -> None:
    _rename_tables(_TABLE_RENAMES)
    _rename_expiry_index(*_EXPIRY_INDEX)


def downgrade() -> None:
    _rename_tables(tuple((new, old) for old, new in reversed(_TABLE_RENAMES)))
    _rename_expiry_index(*reversed(_EXPIRY_INDEX))
