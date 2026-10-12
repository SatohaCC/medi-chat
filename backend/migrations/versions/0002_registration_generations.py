"""不変登録receiptとSQLite公開世代。起動時DDLは禁止。"""

from alembic import op

from backend.infrastructure.persistence.registration_schema import TABLES

revision = "0002_registration_generations"
down_revision = "0001_v3_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in TABLES:
        table.create(op.get_bind(), checkfirst=False)


def downgrade() -> None:
    for table in reversed(TABLES):
        table.drop(op.get_bind(), checkfirst=False)
