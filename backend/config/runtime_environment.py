"""The shared environment loading order used by dev and configured probes."""

import os

from dotenv import load_dotenv

from ..project_paths import BACKEND_DIR, PROJECT_ROOT


def load_runtime_environment() -> None:
    load_dotenv(BACKEND_DIR / ".env.local", override=True)
    load_dotenv(PROJECT_ROOT / ".env.local", override=True)
    load_dotenv(BACKEND_DIR / ".env")
    load_dotenv(PROJECT_ROOT / ".env")
    if os.environ.get("GEMINI_API_KEY") and "GOOGLE_API_KEY" in os.environ:
        del os.environ["GOOGLE_API_KEY"]
