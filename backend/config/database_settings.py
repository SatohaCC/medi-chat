"""アプリ・CLI・Alembicで共有するDB設定の契約。"""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


@dataclass(frozen=True)
class PostgresDatabaseSettings:
    database_url: str = field(repr=False)

    @property
    def is_local(self) -> bool:
        return make_url(self.database_url).host in {"localhost", "127.0.0.1", "::1"}


def resolve_postgres_database_settings(
    *, database_url: str | None = None, environ: Mapping[str, str] | None = None
) -> PostgresDatabaseSettings:
    environment = os.environ if environ is None else environ
    if any(
        key in environment
        for key in (
            "MEDI_CHAT_INDEX_PATH",
            "MEDI_CHAT_IMPORT_ROOT",
            "MEDI_CHAT_IMPORT_DIR",
            "MEDI_CHAT_STRUCTURED_DIR",
        )
    ):
        raise ValueError("Legacy runtime file settings are not supported")
    value = database_url or environment.get("MEDI_CHAT_DATABASE_URL")
    if not value:
        raise ValueError("An explicit PostgreSQL database URL is required")
    try:
        url = make_url(value)
    except ArgumentError, ValueError:
        raise ValueError("Invalid PostgreSQL database configuration") from None
    allowed = {"localhost", "127.0.0.1", "::1"}
    cloud_hosts = {
        host.strip()
        for host in environment.get("MEDI_CHAT_DATABASE_HOSTS", "").split(",")
        if host.strip()
    }
    if environment.get("CI", "").lower() in {"true", "1"}:
        allowed.update(
            host.strip()
            for host in environment.get("MEDI_CHAT_TEST_DATABASE_HOSTS", "").split(",")
            if host.strip()
        )
    if (
        url.drivername not in {"postgresql", "postgresql+psycopg"}
        or url.host not in allowed | cloud_hosts
        or not url.database
        or not url.username
        or (url.host in allowed and bool(url.query))
    ):
        raise ValueError(
            "PostgreSQL requires a named database and an allowed host without URL options"
        )
    if url.host not in allowed:
        # Only TLS policy options are accepted; never allow query parameters to
        # redirect the connection to another host, user or local socket.
        options = dict(url.query)
        if (
            set(options) - {"sslmode", "channel_binding", "sslrootcert"}
            or options.get("sslmode") not in {"require", "verify-full"}
            or (
                options.get("sslmode") == "require"
                and options.get("channel_binding") != "require"
            )
            or (
                "channel_binding" in options and options["channel_binding"] != "require"
            )
            or ("sslrootcert" in options and options["sslrootcert"] != "system")
            or (
                options.get("sslmode") == "verify-full"
                and options.get("sslrootcert") != "system"
            )
        ):
            raise ValueError(
                "Remote PostgreSQL requires explicit TLS and channel binding or system certificate verification"
            )
    return PostgresDatabaseSettings(
        url.set(drivername="postgresql+psycopg").render_as_string(hide_password=False)
    )
