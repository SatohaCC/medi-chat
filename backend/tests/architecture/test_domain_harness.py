"""Domain rules must reject violations, including newly discovered contexts."""

import json
from pathlib import Path

import pytest
from scripts.domain_architecture import check, main


def write(root: Path, files: dict[str, str]) -> None:
    domain = root / "backend/domain"
    domain.mkdir(parents=True, exist_ok=True)
    (domain / "__init__.py").write_text("", encoding="utf-8")
    for relative, source in files.items():
        path = domain / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        (path.parent / "__init__.py").touch()
        path.write_text(source, encoding="utf-8")
    for directory in domain.iterdir():
        if directory.is_dir() and directory.name not in {"foundation", "shared"}:
            identifier = directory / "identifiers.py"
            if not identifier.exists():
                identifier.write_text(
                    "from backend.domain.foundation.primitives.identifiers import EntityStringId\n"
                    "class RecordId(EntityStringId): pass\n",
                    encoding="utf-8",
                )


@pytest.mark.parametrize(
    "path,source,rule",
    [
        ("orders/value_objects.py", "def broken(:", "DOM000"),
        ("orders/helpers.py", "", "DOM001"),
        ("orders/nested/helper.py", "", "DOM001"),
        ("orders/__init__.py", "from .identifiers import RecordId", "DOM002"),
        (
            "orders/entities.py",
            "from backend.application.chat import queries",
            "DOM003",
        ),
        ("orders/services.py", "from ..other.entities import Product", "DOM003"),
        (
            "foundation/value_objects.py",
            "from ..orders.identifiers import RecordId",
            "DOM003",
        ),
        ("shared/services.py", "from ..orders.identifiers import RecordId", "DOM003"),
        ("orders/primitives.py", "from .value_objects import Value", "DOM004"),
        ("orders/value_objects.py", "from . import entities", "DOM004"),
        ("orders/entities.py", "def f():\n    from .services import execute", "DOM004"),
        (
            "orders/identifiers.py",
            "class FirstId: pass\nclass SecondId: pass",
            "DOM005",
        ),
        ("orders/identifiers.py", "class RecordId(str): pass", "DOM005"),
        ("orders/identifiers.py", "from .primitives import Value", "DOM005"),
        (
            "orders/services.py",
            "import socket\nsocket.create_connection(('test', 443))",
            "DOM006",
        ),
        ("orders/services.py", "import subprocess as sp\nsp.run(['test'])", "DOM006"),
        ("orders/services.py", "import urllib.request", "DOM006"),
        ("orders/services.py", "from urllib import request", "DOM006"),
        ("orders/services.py", "from importlib import import_module as load", "DOM006"),
        ("orders/services.py", "__import__('socket')", "DOM006"),
        (
            "orders/services.py",
            "from builtins import open as read\nread('test')",
            "DOM006",
        ),
        ("orders/services.py", "import pydantic", "DOM006"),
        ("orders/services.py", "import shelve", "DOM006"),
        ("orders/services.py", "import dbm", "DOM006"),
        ("orders/services.py", "print('domain output')", "DOM006"),
        (
            "orders/services.py",
            "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from backend.infrastructure.persistence import postgres_runtime",
            "DOM003",
        ),
        ("orders/services.py", "from .primitives import *", "DOM006"),
        (
            "orders/value_objects.py",
            "from dataclasses import dataclass as dc\n@dc\nclass Value: pass",
            "DOM007",
        ),
        (
            "orders/value_objects.py",
            "import dataclasses as dc\n@dc.dataclass\nclass Value: pass",
            "DOM007",
        ),
        ("orders/value_objects.py", "class Value: pass", "DOM007"),
        (
            "orders/value_objects.py",
            "from dataclasses import dataclass\nimport typing\n@dataclass(frozen=True)\nclass Value:\n    items: typing.List[bool]",
            "DOM008",
        ),
        (
            "orders/value_objects.py",
            "from dataclasses import dataclass\nfrom typing import List as Items\n@dataclass(frozen=True)\nclass Value:\n    items: Items[bool]",
            "DOM008",
        ),
        (
            "orders/value_objects.py",
            "from dataclasses import dataclass\ntype Items = list[bool]\n@dataclass(frozen=True)\nclass Value:\n    items: Items",
            "DOM008",
        ),
        (
            "orders/value_objects.py",
            "from dataclasses import dataclass\n@dataclass(frozen=True)\nclass Value:\n    items: 'list[bool]'",
            "DOM008",
        ),
        (
            "orders/entities.py",
            "from dataclasses import dataclass\n@dataclass(frozen=True)\nclass Order:\n    name: str",
            "DOM009",
        ),
        (
            "orders/value_objects.py",
            "from dataclasses import dataclass\ntype Name = str\n@dataclass(frozen=True)\nclass Value:\n    name: Name",
            "DOM009",
        ),
        (
            "orders/value_objects.py",
            "class Value:\n    def create(self): pass",
            "DOM010",
        ),
        (
            "orders/value_objects.py",
            "class Value:\n    def __post_init__(self):\n        object.__setattr__(self, 'items', tuple(self.items))",
            "DOM011",
        ),
        ("orders/primitives.py", "class Value(str): pass", "DOM012"),
        ("orders/repositories.py", "class Store: pass", "DOM012"),
        (
            "orders/services.py",
            "from dataclasses import dataclass as dc\nclass Outer:\n    @dc\n    class Hidden:\n        items: list[str]",
            "DOM012",
        ),
        (
            "orders/value_objects.py",
            "from dataclasses import dataclass\n@dataclass(frozen=True)\nclass Value:\n    items = []",
            "DOM009",
        ),
        (
            "orders/services.py",
            'def f(value: "backend.application.chat.queries.models.ChatResponse"): pass',
            "DOM003",
        ),
        (
            "orders/primitives.py",
            'def f(value: "backend.domain.orders.value_objects.Value"): pass',
            "DOM004",
        ),
        (
            "orders/value_objects.py",
            "from dataclasses import dataclass, field\n@dataclass(frozen=True)\nclass Value:\n    items: tuple[bool, ...] = field(default_factory=list)",
            "DOM008",
        ),
        (
            "orders/value_objects.py",
            "class Value:\n    def __post_init__(self):\n        self.items = tuple(self.items)",
            "DOM011",
        ),
        (
            "orders/value_objects.py",
            "class Value:\n    def __post_init__(self):\n        if not isinstance(self.items, tuple): raise TypeError()",
            "DOM011",
        ),
    ],
)
def test_forbidden_examples(tmp_path, path, source, rule):
    write(tmp_path, {path: source})
    findings = check(tmp_path)
    assert any(f.rule == rule and f.line > 0 for f in findings), findings


def test_valid_domain_with_new_context_and_aliases(tmp_path):
    write(
        tmp_path,
        {
            "new_context/primitives.py": "from backend.domain.foundation.primitives.base import DomainPrimitive\nclass Name(DomainPrimitive[str]): pass",
            "new_context/value_objects.py": "import dataclasses as dc\nfrom .primitives import Name\n@dc.dataclass(frozen=True)\nclass Value:\n    names: tuple[Name, ...]\n    enabled: bool = False",
            "new_context/services.py": "from urllib.parse import urlparse\nfrom ..other.identifiers import RecordId\nfrom typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from .value_objects import Value",
            "other/services.py": "",
        },
    )
    assert check(tmp_path) == []


def test_new_context_cannot_hide_missing_identifier(tmp_path):
    write(tmp_path, {"new_context/entities.py": ""})
    (tmp_path / "backend/domain/new_context/identifiers.py").unlink()
    assert any(f.rule == "DOM005" for f in check(tmp_path))


def test_checker_never_executes_source(tmp_path):
    write(tmp_path, {"orders/services.py": "raise RuntimeError('must not execute')"})
    assert check(tmp_path) == []


def test_cli_contract_and_cwd_independence(tmp_path, monkeypatch, capsys):
    write(tmp_path, {"orders/services.py": "import socket"})
    monkeypatch.chdir(tmp_path)
    assert main(["--root", str(tmp_path), "--json"]) == 1
    assert json.loads(capsys.readouterr().out)[0]["rule"] == "DOM006"
    assert main(["--root", str(tmp_path), "--context", "missing"]) == 2
    assert main(["--root", str(tmp_path / "missing")]) == 2


def test_current_repository_passes_all_rules():
    assert check(Path(__file__).resolve().parents[3]) == []


def test_internal_cycles_are_rejected(tmp_path):
    write(
        tmp_path,
        {
            "foundation/primitives/base.py": "from .primitives import BaseString",
            "foundation/primitives/primitives.py": "from .base import DomainPrimitive",
        },
    )
    assert any(f.rule == "DOM013" for f in check(tmp_path))


@pytest.mark.parametrize(
    "type_source,rule", [("list[bool]", "DOM008"), ("str", "DOM009")]
)
def test_imported_type_alias_cannot_hide_invalid_model_field(
    tmp_path, type_source, rule
):
    write(
        tmp_path,
        {
            "shared/primitives.py": f"type Payload = {type_source}",
            "orders/value_objects.py": "from dataclasses import dataclass\nfrom ..shared.primitives import Payload\n@dataclass(frozen=True)\nclass Value:\n    payload: Payload",
        },
    )
    assert any(f.rule == rule for f in check(tmp_path))


def test_identifier_base_module_alias_is_allowed(tmp_path):
    write(
        tmp_path,
        {
            "orders/identifiers.py": "from backend.domain.foundation.primitives import identifiers as ids\nclass RecordId(ids.EntityStringId): pass",
        },
    )
    assert check(tmp_path) == []


def test_context_filter_and_success_exit(tmp_path, capsys):
    write(tmp_path, {"orders/services.py": "", "other/services.py": "import socket"})
    assert check(tmp_path, context="orders") == []
    assert main(["--root", str(tmp_path), "--context", "orders"]) == 0
    assert "0 findings" in capsys.readouterr().out


def test_standard_lint_and_ci_enforce_domain_harness():
    root = Path(__file__).resolve().parents[3]
    scripts = json.loads((root / "backend/package.json").read_text(encoding="utf-8"))[
        "scripts"
    ]
    assert "pnpm run lint:domain && pnpm run lint:domain:harness" in scripts["lint"]
    assert "scripts/domain_architecture.py" in scripts["lint:domain"]
    assert "test_domain_harness.py" in scripts["lint:domain:harness"]
    assert "python scripts/domain_architecture.py" in (
        root / ".github/workflows/postgres-contracts.yml"
    ).read_text(encoding="utf-8")


def test_missing_package_and_empty_nested_directory_are_rejected(tmp_path):
    write(tmp_path, {"orders/services.py": ""})
    directory = tmp_path / "backend/domain/orders"
    (directory / "__init__.py").unlink()
    (directory / "hidden_models").mkdir()
    findings = check(tmp_path)
    assert any(
        f.rule == "DOM001" and f.path.endswith("orders/__init__.py") for f in findings
    )
    assert any(
        f.rule == "DOM001" and f.path.endswith("hidden_models") for f in findings
    )


def test_public_id_module_cannot_publish_an_extra_operation(tmp_path):
    write(tmp_path, {"orders/services.py": ""})
    path = tmp_path / "backend/domain/orders/identifiers.py"
    path.write_text(
        path.read_text(encoding="utf-8") + "def helper(): pass\n", encoding="utf-8"
    )
    assert any(f.rule == "DOM005" for f in check(tmp_path))
