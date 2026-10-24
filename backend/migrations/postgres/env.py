"""Explicit PostgreSQL migration environment; runtime never invokes this."""

from alembic import context
from backend.infrastructure.persistence.postgres_engine import create_postgres_engine
from backend.infrastructure.persistence.postgres_schema import metadata
from sqlalchemy import inspect

config = context.config
connection = config.attributes.get("connection")


def migrate(connection):
    existing = set(inspect(connection).get_table_names())
    if existing and "alembic_version" not in existing:
        raise ValueError("Refusing an unmanaged nonempty PostgreSQL schema")
    context.configure(connection=connection, target_metadata=metadata)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(
        url="postgresql+psycopg://", target_metadata=metadata, literal_binds=True
    )
    with context.begin_transaction():
        context.run_migrations()
elif connection is not None:
    migrate(connection)
else:
    arguments = context.get_x_argument(as_dictionary=True)
    database_url = arguments.get("database_url")
    if not database_url:
        raise ValueError("Migration requires explicit -x database_url")
    engine = create_postgres_engine(database_url)
    try:
        with engine.begin() as connection:
            migrate(connection)
    finally:
        engine.dispose()
