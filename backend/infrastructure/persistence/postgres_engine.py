"""Composition-owned psycopg pool; no DDL or implicit fallback."""

import os
import re

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from backend.config.database_settings import resolve_postgres_database_settings


def create_postgres_engine(database_url: str, *, schema: str = "public") -> Engine:
    if not re.fullmatch(r"(?:public|medi_chat_test_[a-z0-9_]+)", schema):
        raise ValueError("Unsupported PostgreSQL schema")
    settings = resolve_postgres_database_settings(
        database_url=database_url,
        environ={
            key: os.environ[key]
            for key in ("CI", "MEDI_CHAT_TEST_DATABASE_HOSTS")
            if key in os.environ
        },
    )
    return create_engine(
        settings.database_url,
        pool_size=5,
        max_overflow=0,
        pool_timeout=10,
        pool_pre_ping=True,
        connect_args={
            "connect_timeout": 10,
            "options": f"-csearch_path={schema} -cstatement_timeout=30000 -clock_timeout=10000 -cidle_in_transaction_session_timeout=60000",
        },
    )
