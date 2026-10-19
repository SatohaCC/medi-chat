"""Read-only validation of a prepared PostgreSQL publication."""

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from .postgres_integrity import PROJECTION_FINGERPRINT


def verify_postgres_readiness(engine: Engine, *, projections: bool = True) -> None:
    try:
        with engine.connect().execution_options(
            isolation_level="REPEATABLE READ"
        ) as connection:
            connection.execute(text("SET TRANSACTION READ ONLY"))
            revision = (
                connection.execute(text("SELECT version_num FROM alembic_version"))
                .scalars()
                .all()
            )
            if revision != ["pg_20261019_03"]:
                raise RuntimeError(
                    "schema_not_ready: run explicit PostgreSQL migrations"
                )
            pointer = connection.execute(
                text("SELECT generation_id FROM registration_state WHERE singleton=1")
            ).scalar_one_or_none()
            if pointer is None:
                raise RuntimeError("initial_registration_required")
            invalid = connection.execute(
                text("""
                SELECT EXISTS (
                    SELECT 1 FROM attachment_versions
                    WHERE payload_fingerprint <> md5(structure::text || catalogue::text)
                       OR structure->>'schema_version' IS DISTINCT FROM '1'
                       OR structure->>'transformer_version' IS DISTINCT FROM 'attachment-domain.v1'
                )
            """)
            ).scalar_one()
            if invalid:
                raise RuntimeError("stored_structure_invalid")
            invalid = connection.execute(
                text(f"""
                SELECT EXISTS (
                    SELECT 1 FROM attachment_versions v JOIN registration_receipts r USING(version_id)
                    WHERE octet_length(v.source) <> v.byte_size
                       OR encode(sha256(v.source), 'hex') <> r.source_sha256
                ) OR EXISTS (
                    SELECT 1 FROM attachment_assets
                    WHERE octet_length(content) <> byte_size OR encode(sha256(content), 'hex') <> source_sha256
                ) OR EXISTS (
                    SELECT 1 FROM attachment_versions
                    WHERE :projections AND projection_fingerprint <> {PROJECTION_FINGERPRINT}
                )
            """),
                {"projections": projections},
            ).scalar_one()
            if invalid:
                raise RuntimeError("payload_integrity_invalid")
            invalid = connection.execute(
                text("""
                SELECT NOT EXISTS (SELECT 1 FROM generation_memberships WHERE generation_id=:pointer)
                    OR EXISTS (
                        (SELECT yj_code, version_id FROM active_registrations
                         EXCEPT SELECT yj_code, version_id FROM generation_memberships WHERE generation_id=:pointer)
                        UNION ALL
                        (SELECT yj_code, version_id FROM generation_memberships WHERE generation_id=:pointer
                         EXCEPT SELECT yj_code, version_id FROM active_registrations)
                    )
                    OR EXISTS (
                        SELECT 1 FROM generation_memberships m
                        JOIN registration_receipts r ON r.version_id=m.version_id
                        LEFT JOIN attachment_versions v ON v.version_id=m.version_id
                        WHERE m.generation_id=:pointer AND (r.artifacts_deleted OR v.version_id IS NULL)
                    )
            """),
                {"pointer": pointer},
            ).scalar_one()
            if invalid:
                raise RuntimeError("publication_state_invalid")
    except SQLAlchemyError:
        raise RuntimeError(
            "schema_not_ready: PostgreSQL connection, permissions or schema unavailable"
        ) from None
