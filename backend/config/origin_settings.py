"""Explicit local/custom origins plus deployment-owned Vercel URLs."""

import os
from collections.abc import Mapping


def read_allowed_origins(environ: Mapping[str, str] | None = None) -> list[str]:
    environment = os.environ if environ is None else environ
    origins = [
        origin.strip()
        for origin in environment.get(
            "ALLOWED_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001",
        ).split(",")
        if origin.strip()
    ]
    if environment.get("VERCEL") == "1":
        for name in (
            "VERCEL_URL",
            "VERCEL_PROJECT_PRODUCTION_URL",
            "VERCEL_BRANCH_URL",
        ):
            host = environment.get(name, "").strip()
            if host and "/" not in host and ":" not in host:
                origins.append(f"https://{host}")
    return list(dict.fromkeys(origins))
