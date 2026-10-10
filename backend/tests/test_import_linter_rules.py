"""実際のImport Linter契約を新規コンテキストと間接依存で検証する。"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("sources", "broken"),
    [
        ({"domain/new_one/model.py": "from ..new_two import identifiers"}, False),
        (
            {"domain/new_one/model.py": "import backend.domain.new_two.identifiers"},
            False,
        ),
        ({"domain/shared/model.py": "from ..new_two import identifiers"}, True),
        ({"domain/foundation/model.py": "from ..new_two import identifiers"}, True),
        ({"domain/new_two/identifiers.py": "from . import model"}, True),
        (
            {
                "domain/new_one/model.py": "from ..new_two import identifiers",
                "domain/new_two/identifiers.py": "from . import model",
            },
            True,
        ),
        (
            {
                "domain/new_two/identifiers.py": "from ..foundation.primitives import identifiers"
            },
            False,
        ),
        ({"domain/new_two/identifiers.py": "from ..foundation import model"}, True),
        ({"domain/new_two/identifiers.py": "from ..shared import model"}, True),
        ({"domain/new_two/identifiers.py": "import dataclasses"}, False),
        ({"domain/new_one/model.py": "from ..new_two import model"}, True),
        ({"domain/new_one/model.py": "import backend.domain.new_two.model"}, True),
        (
            {
                "domain/new_one/model.py": "from . import helper",
                "domain/new_one/helper.py": "from ..new_two import model",
            },
            True,
        ),
        ({"domain/shared/model.py": "from ..new_one import model"}, True),
        ({"domain/foundation/model.py": "from ..new_one import model"}, True),
        ({"domain/foundation/model.py": "from ..shared import model"}, True),
        ({"domain/new_one/model.py": "from ...application import model"}, True),
        (
            {
                "domain/new_one/model.py": "from ... import bridge",
                "bridge.py": "from .presentation import model",
            },
            True,
        ),
        (
            {
                "domain/new_one/model.py": "from ..shared import model\nfrom ..foundation import model\nfrom .. import json_types"
            },
            False,
        ),
        ({"domain/shared/model.py": "from ..foundation import model"}, False),
        (
            {
                "application/model.py": "from ..domain.new_one import model\nfrom ..domain.new_two import model"
            },
            False,
        ),
        ({"infrastructure/model.py": "from ..domain.new_one import model"}, False),
    ],
)
def test_import_linter_enforces_configured_contracts(tmp_path, sources, broken):
    configuration = (ROOT / "backend/pyproject.toml").read_text(encoding="utf-8")
    configuration = (
        "[tool.importlinter]"
        + configuration.split("[tool.importlinter]", 1)[1].split("[tool.ruff]", 1)[0]
    )
    config_path = tmp_path / "pyproject.toml"
    config_path.write_text(configuration, encoding="utf-8")
    package = tmp_path / "backend"
    for name in [
        "",
        "domain",
        "domain/new_one",
        "domain/new_two",
        "domain/shared",
        "domain/foundation",
        "application",
        "infrastructure",
        "presentation",
    ]:
        directory = package / name
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "__init__.py").write_text("", encoding="utf-8")
        (directory / "model.py").write_text("", encoding="utf-8")
    (package / "domain/json_types.py").write_text("", encoding="utf-8")
    foundation_primitives = package / "domain/foundation/primitives"
    foundation_primitives.mkdir()
    (foundation_primitives / "__init__.py").write_text("", encoding="utf-8")
    (foundation_primitives / "identifiers.py").write_text("", encoding="utf-8")
    for context in ("new_one", "new_two"):
        (package / "domain" / context / "identifiers.py").write_text(
            "", encoding="utf-8"
        )
    for relative, source in sources.items():
        (package / relative).write_text(source + "\n", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from importlinter.cli import lint_imports_command; lint_imports_command()",
            "--config",
            str(config_path),
            "--no-cache",
        ],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(tmp_path)},
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == int(broken), result.stdout + result.stderr
    assert ("BROKEN" in result.stdout) == broken
