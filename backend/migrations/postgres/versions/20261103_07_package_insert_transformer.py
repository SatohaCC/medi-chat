"""Update persisted package insert transformer metadata."""

from alembic import op
from sqlalchemy import text

revision = "pg_20261103_07"
down_revision = "pg_20261103_06"
branch_labels = None
depends_on = None

_TRANSFORMER_VERSIONS = (
    "attachment-domain.v1",
    "package-insert-domain.v1",
)


def _set_transformer_version(expected, target):
    connection = op.get_bind()
    unsupported = connection.execute(
        text(
            "SELECT EXISTS ("
            "SELECT 1 FROM package_insert_versions "
            "WHERE structure->>'transformer_version' IS DISTINCT FROM :expected"
            ")"
        ),
        {"expected": expected},
    ).scalar_one()
    if unsupported:
        raise RuntimeError(
            "Refusing package insert transformer migration with unsupported stored versions"
        )

    connection.execute(
        text(
            "UPDATE package_insert_versions "
            "SET structure = jsonb_set("
            "structure, '{transformer_version}', to_jsonb(CAST(:target AS text))"
            "), payload_fingerprint = md5(jsonb_set("
            "structure, '{transformer_version}', to_jsonb(CAST(:target AS text))"
            ")::text || catalogue::text) "
            "WHERE structure->>'transformer_version' = :expected"
        ),
        {"expected": expected, "target": target},
    )


def upgrade():
    _set_transformer_version(*_TRANSFORMER_VERSIONS)


def downgrade():
    _set_transformer_version(*reversed(_TRANSFORMER_VERSIONS))
