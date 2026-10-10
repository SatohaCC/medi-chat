"""回答生成の既定設定を外側で解決する。"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class GenerationDefaults:
    provider: str
    model: str


def read_generation_defaults() -> GenerationDefaults:
    return GenerationDefaults(
        os.environ.get("DEFAULT_PROVIDER", "openai"),
        os.environ.get("DEFAULT_MODEL", "gpt-6-luna"),
    )
