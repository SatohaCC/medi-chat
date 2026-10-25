"""Application identity and rotating refresh sessions."""

from alembic import op
from backend.infrastructure.persistence.schemas.authentication_tables import AUTH_TABLES

revision = "pg_20261024_05"
down_revision = "pg_20261019_04"
branch_labels = None
depends_on = None


def upgrade():
    for table in AUTH_TABLES:
        table.create(op.get_bind(), checkfirst=False)


def downgrade():
    for table in reversed(AUTH_TABLES):
        table.drop(op.get_bind(), checkfirst=False)
