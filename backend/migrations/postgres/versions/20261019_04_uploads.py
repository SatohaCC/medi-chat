"""Bounded expiring upload sessions shared by Function instances."""

import sqlalchemy as sa
from alembic import op

revision = "pg_20261019_04"
down_revision = "pg_20261019_03"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "attachment_uploads",
        sa.Column("upload_id", sa.Text, primary_key=True),
        sa.Column("filename", sa.Text, nullable=False),
        sa.Column("byte_size", sa.Integer, nullable=False),
        sa.Column("source_sha256", sa.Text, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("document_id", sa.Text, nullable=True),
        sa.CheckConstraint(
            "byte_size BETWEEN 1 AND 10485760", name="upload_size_limit"
        ),
    )
    op.create_index(
        "ix_attachment_uploads_expires_at", "attachment_uploads", ["expires_at"]
    )
    op.create_table(
        "attachment_upload_parts",
        sa.Column(
            "upload_id",
            sa.Text,
            sa.ForeignKey("attachment_uploads.upload_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("part_index", sa.Integer, primary_key=True),
        sa.Column("content", sa.LargeBinary, nullable=False),
        sa.CheckConstraint("part_index BETWEEN 0 AND 3", name="upload_part_index"),
        sa.CheckConstraint(
            "octet_length(content) BETWEEN 1 AND 3145728", name="upload_part_size"
        ),
    )


def downgrade():
    op.drop_table("attachment_upload_parts")
    op.drop_table("attachment_uploads")
