"""PostgreSQL version payloads and small publication membership metadata."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    MetaData,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()
receipts = Table(
    "registration_receipts",
    metadata,
    Column("version_id", Text, primary_key=True),
    Column("document_id", Text, nullable=False),
    Column("source_sha256", Text, nullable=False),
    Column("sequence", BigInteger, unique=True, nullable=False),
    Column("revised_at", Text, nullable=False),
    Column("yj_codes", JSONB, nullable=False),
    Column("replaced", JSONB, nullable=False),
    Column("cleanup_targets", JSONB, nullable=False),
    Column("result", JSONB, nullable=False),
    Column("artifacts_deleted", Boolean, nullable=False),
    Column("cleanup_reason", Text, nullable=False),
)
versions = Table(
    "attachment_versions",
    metadata,
    Column(
        "version_id",
        Text,
        ForeignKey("registration_receipts.version_id"),
        primary_key=True,
    ),
    Column("structure", JSONB, nullable=False),
    Column("catalogue", JSONB, nullable=False),
    Column("payload_fingerprint", Text, nullable=False),
    Column("projection_fingerprint", Text, nullable=False),
    Column("source", LargeBinary, nullable=False),
    Column("filename", Text, nullable=False),
    Column("byte_size", BigInteger, nullable=False),
    Column("validation", JSONB, nullable=False),
    CheckConstraint("byte_size = octet_length(source)", name="source_byte_size"),
)
assets = Table(
    "attachment_assets",
    metadata,
    Column(
        "version_id",
        Text,
        ForeignKey("attachment_versions.version_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("logical_name", Text, primary_key=True),
    Column("media_type", Text, nullable=False),
    Column("source_sha256", Text, nullable=False),
    Column("byte_size", BigInteger, nullable=False),
    Column("content", LargeBinary, nullable=False),
    CheckConstraint("byte_size = octet_length(content)", name="asset_byte_size"),
)
units = Table(
    "search_units",
    metadata,
    Column(
        "version_id",
        Text,
        ForeignKey("attachment_versions.version_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("unit_id", Text, primary_key=True),
    Column("position", Integer, nullable=False),
    Column("document_key", Text, nullable=False),
    Column("section_code", Text, nullable=False),
    Column("kind", Text, nullable=False),
    Column("query_text", Text, nullable=False),
    Column("payload_json", Text, nullable=False),
    Column("payload", JSONB, nullable=False),
)
Index("units_version_section", units.c.version_id, units.c.section_code)
unit_products = Table(
    "unit_products",
    metadata,
    Column(
        "version_id",
        Text,
        ForeignKey("attachment_versions.version_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("yj_code", Text, primary_key=True),
    Column("section_code", Text, primary_key=True),
)
active = Table(
    "active_registrations",
    metadata,
    Column("yj_code", Text, primary_key=True),
    Column(
        "version_id", Text, ForeignKey("attachment_versions.version_id"), nullable=False
    ),
)
generations = Table(
    "registration_generations",
    metadata,
    Column("generation_id", Text, primary_key=True),
    Column("fingerprint", Text, nullable=False),
)
memberships = Table(
    "generation_memberships",
    metadata,
    Column(
        "generation_id",
        Text,
        ForeignKey("registration_generations.generation_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("yj_code", Text, primary_key=True),
    Column(
        "version_id", Text, ForeignKey("attachment_versions.version_id"), nullable=False
    ),
)
state = Table(
    "registration_state",
    metadata,
    Column("singleton", Integer, primary_key=True),
    Column("generation_id", Text, ForeignKey("registration_generations.generation_id")),
    Column("sequence", BigInteger, nullable=False),
    CheckConstraint("singleton = 1", name="one_publication_state"),
)
