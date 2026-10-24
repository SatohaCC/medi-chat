"""Credential and refresh tables; DDL is applied only by explicit migrations."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    Integer,
    Table,
    Text,
    UniqueConstraint,
)

from .postgres_schema import metadata

users = Table(
    "auth_users",
    metadata,
    Column("user_id", Text, primary_key=True),
    Column("login_id", Text, unique=True, nullable=False),
    Column("active", Boolean, nullable=False),
    Column("revision", Integer, nullable=False),
)
identities = Table(
    "auth_identities",
    metadata,
    Column("issuer", Text, primary_key=True),
    Column("subject", Text, primary_key=True),
    Column("user_id", Text, ForeignKey("auth_users.user_id"), nullable=False),
)
credentials = Table(
    "auth_credentials",
    metadata,
    Column("user_id", Text, ForeignKey("auth_users.user_id"), primary_key=True),
    Column("password_hash", Text, nullable=False),
)
families = Table(
    "auth_sessions",
    metadata,
    Column("family_id", Text, primary_key=True),
    Column(
        "user_id", Text, ForeignKey("auth_users.user_id"), nullable=False, index=True
    ),
    Column("expires_at", BigInteger, nullable=False, index=True),
    Column("revoked", Boolean, nullable=False),
)
refresh_tokens = Table(
    "auth_refresh_tokens",
    metadata,
    Column("digest", Text, primary_key=True),
    Column(
        "family_id",
        Text,
        ForeignKey("auth_sessions.family_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("used", Boolean, nullable=False),
)
attempts = Table(
    "auth_login_attempts",
    metadata,
    Column("bucket", Text, primary_key=True),
    Column("window", BigInteger, primary_key=True),
    Column("count", Integer, nullable=False),
    UniqueConstraint("bucket", "window"),
)

AUTH_TABLES = (users, identities, credentials, families, refresh_tokens, attempts)
