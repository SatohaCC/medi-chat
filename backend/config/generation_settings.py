"""回答生成の既定設定を外側で解決する。"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class GenerationDefaults:
    provider: str
    model: str

    def resolve(self, provider: str | None, model: str | None) -> GenerationDefaults:
        selected = provider or self.provider
        if model:
            return GenerationDefaults(selected, model)
        if selected == self.provider:
            return GenerationDefaults(selected, self.model)
        return GenerationDefaults(
            selected,
            {
                "openai": "gpt-6-luna",
                "gemini": "gemini-3.8-flash",
            }[selected],
        )


def read_generation_defaults() -> GenerationDefaults:
    return GenerationDefaults(
        os.environ.get("DEFAULT_PROVIDER", "openai"),
        os.environ.get("DEFAULT_MODEL", "gpt-6-luna"),
    )
