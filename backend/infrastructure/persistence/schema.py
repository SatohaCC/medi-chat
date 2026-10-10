"""添付文書索引v3の通常tableとindexを表すCore metadata。"""

from sqlalchemy import Column, Index, MetaData, Table, Text

metadata = MetaData()

documents = Table(
    "documents",
    metadata,
    Column("document_key", Text, primary_key=True, nullable=True),
    Column("payload_json", Text, nullable=False),
)

medicines = Table(
    "medicines",
    metadata,
    Column("document_key", Text, nullable=False),
    Column("yj_code", Text),
    Column("brand_name", Text, nullable=False),
    Column("generic_name", Text, nullable=False),
    Column("english_name", Text, nullable=False),
    Column("hiragana_name", Text, nullable=False),
    Column("pmda_url", Text, nullable=False),
    Column("revision_json", Text, nullable=False),
)
Index("idx_medicines_yj", medicines.c.yj_code)
Index("idx_medicines_doc", medicines.c.document_key)

units = Table(
    "units",
    metadata,
    Column("unit_id", Text, primary_key=True, nullable=True),
    Column("document_key", Text, nullable=False),
    Column("section_code", Text, nullable=False),
    Column("kind", Text, nullable=False),
    Column("payload_json", Text, nullable=False),
)
Index(
    "units_by_document_section",
    units.c.document_key,
    units.c.section_code,
    units.c.kind,
)

index_meta = Table(
    "index_meta",
    metadata,
    Column("key", Text, primary_key=True, nullable=True),
    Column("value", Text, nullable=False),
)
