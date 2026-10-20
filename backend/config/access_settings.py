"""Deployment access policy; never expose the shared secret in diagnostics."""

import os
from collections.abc import Mapping


def read_access_secret(
    environ: Mapping[str, str] | None = None, *, required: bool = False
) -> str | None:
    environment = os.environ if environ is None else environ
    secret = environment.get("APP_SECRET_KEY", "")
    if not secret and not required and environment.get("VERCEL") != "1":
        return None
    if not 32 <= len(secret.encode("utf-8")) <= 1024 or secret.isspace():
        raise ValueError("APP_SECRET_KEY must be configured with 32 to 1024 bytes")
    return secret
