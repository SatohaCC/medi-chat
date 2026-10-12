import os
from collections.abc import Mapping
from pathlib import Path

from ..project_paths import resolve_project_path


def resolve_import_directory(*, environ: Mapping[str, str] | None = None) -> Path:
    environment = os.environ if environ is None else environ
    return resolve_project_path(
        Path(environment.get("MEDI_CHAT_IMPORT_DIR", "data/pmda/imports"))
    )
