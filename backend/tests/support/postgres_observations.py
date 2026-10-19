"""Read-only observations of test-owned PostgreSQL schemas."""

from sqlalchemy import text


def digest(engine):
    with engine.connect() as connection:
        names = (
            connection.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname=current_schema() ORDER BY tablename"
                )
            )
            .scalars()
            .all()
        )
        return tuple(
            (
                name,
                connection.execute(
                    text(
                        f"SELECT md5(COALESCE(string_agg(value, chr(10) ORDER BY value),'')) FROM (SELECT to_jsonb(t)::text value FROM \"{name}\" t) q"
                    )
                ).scalar_one(),
            )
            for name in names
        )
