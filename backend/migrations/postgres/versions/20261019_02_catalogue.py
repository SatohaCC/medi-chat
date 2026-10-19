"""Small version catalogue, deterministic row order and scoped unit membership."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "pg_20261019_02"
down_revision = "pg_20261019_01"
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
    op.add_column("attachment_versions", sa.Column("catalogue", JSONB, nullable=False))
    op.add_column("search_units", sa.Column("position", sa.Integer, nullable=False))
    op.create_table(
        "unit_products",
        sa.Column(
            "version_id",
            sa.Text,
            sa.ForeignKey("attachment_versions.version_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("yj_code", sa.Text, primary_key=True),
        sa.Column("section_code", sa.Text, primary_key=True),
    )


def downgrade():
    op.drop_table("unit_products")
    op.drop_column("search_units", "position")
    op.drop_column("attachment_versions", "catalogue")
