"""The shared environment loading order used by dev and configured probes."""

import os

from dotenv import dotenv_values
from dotenv.variables import parse_variables

from ..project_paths import PROJECT_ROOT


def load_runtime_environment() -> None:
    if os.environ.get("PYTHON_DOTENV_DISABLED", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return
    values: dict[str, str | None] = {}
    for path in (PROJECT_ROOT / ".env.local",):
        for name, value in dotenv_values(path, interpolate=False).items():
            environment = {**values, **os.environ}
            values[name] = (
                None
                if value is None
                else "".join(
                    atom.resolve(environment) for atom in parse_variables(value)
                )
            )
    for name, value in values.items():
        if value is not None:
            os.environ.setdefault(name, value)
    if os.environ.get("GEMINI_API_KEY") and "GOOGLE_API_KEY" in os.environ:
        del os.environ["GOOGLE_API_KEY"]
