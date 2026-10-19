"""PostgreSQL-only attachment storage and publication state."""

from alembic import op
from backend.migrations.postgres.initial_schema import metadata, state

revision = "pg_20261019_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    metadata.create_all(op.get_bind())
    op.get_bind().execute(
        state.insert().values(singleton=1, generation_id=None, sequence=0)
    )


def downgrade():
    metadata.drop_all(op.get_bind())
