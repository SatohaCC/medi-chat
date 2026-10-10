"""現行v3索引と互換の初期schema。"""

from alembic import op
from sqlalchemy import Column, Text

revision = "0001_v3_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documents",
        Column("document_key", Text, primary_key=True, nullable=True),
        Column("payload_json", Text, nullable=False),
    )
    op.create_table(
        "medicines",
        Column("document_key", Text, nullable=False),
        Column("yj_code", Text),
        Column("brand_name", Text, nullable=False),
        Column("generic_name", Text, nullable=False),
        Column("english_name", Text, nullable=False),
        Column("hiragana_name", Text, nullable=False),
        Column("pmda_url", Text, nullable=False),
        Column("revision_json", Text, nullable=False),
    )
    op.create_index("idx_medicines_yj", "medicines", ["yj_code"])
    op.create_index("idx_medicines_doc", "medicines", ["document_key"])
    op.create_table(
        "units",
        Column("unit_id", Text, primary_key=True, nullable=True),
        Column("document_key", Text, nullable=False),
        Column("section_code", Text, nullable=False),
        Column("kind", Text, nullable=False),
        Column("payload_json", Text, nullable=False),
    )
    op.create_index(
        "units_by_document_section", "units", ["document_key", "section_code", "kind"]
    )
    op.create_table(
        "index_meta",
        Column("key", Text, primary_key=True, nullable=True),
        Column("value", Text, nullable=False),
    )
    op.execute(
        """CREATE VIRTUAL TABLE unit_fts USING fts5(
            unit_id UNINDEXED,
            document_key UNINDEXED,
            section_code UNINDEXED,
            kind UNINDEXED,
            query_text,
            drug_name,
            tokenize='trigram'
        )"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE unit_fts")
    op.drop_table("index_meta")
    op.drop_index("units_by_document_section", table_name="units")
    op.drop_table("units")
    op.drop_index("idx_medicines_doc", table_name="medicines")
    op.drop_index("idx_medicines_yj", table_name="medicines")
    op.drop_table("medicines")
    op.drop_table("documents")
