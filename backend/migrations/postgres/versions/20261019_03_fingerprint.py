"""Readiness fingerprint of constructor-validated JSON payloads."""

import sqlalchemy as sa
from alembic import op

revision = "pg_20261019_03"
down_revision = "pg_20261019_02"
branch_labels = None
depends_on = None


def upgrade():
    if (
        op.get_bind()
        .execute(sa.text("SELECT count(*) FROM attachment_versions"))
        .scalar_one()
    ):
        raise ValueError(
            "Create a fresh PostgreSQL database and register original sources; old derived projections are not migrated"
        )
    op.add_column(
        "attachment_versions", sa.Column("payload_fingerprint", sa.Text, nullable=False)
    )
    op.add_column(
        "attachment_versions",
        sa.Column("projection_fingerprint", sa.Text, nullable=False),
    )


def downgrade():
    op.drop_column("attachment_versions", "projection_fingerprint")
    op.drop_column("attachment_versions", "payload_fingerprint")
