"""The shared environment loading order used by dev and configured probes."""

import os

from dotenv import dotenv_values

from ..project_paths import BACKEND_DIR, PROJECT_ROOT


def load_runtime_environment() -> None:
    if os.environ.get("PYTHON_DOTENV_DISABLED", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return
    values = {}
    for path in (
        PROJECT_ROOT / ".env",
        BACKEND_DIR / ".env",
        BACKEND_DIR / ".env.local",
        PROJECT_ROOT / ".env.local",
    ):
        values.update(dotenv_values(path))
    for name, value in values.items():
        if value is not None:
            os.environ.setdefault(name, value)
    if os.environ.get("GEMINI_API_KEY") and "GOOGLE_API_KEY" in os.environ:
        del os.environ["GOOGLE_API_KEY"]
