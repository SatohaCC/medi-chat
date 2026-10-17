"""内側の層が外部技術や実IOに依存しないことを検証する。"""

from __future__ import annotations

import ast
import importlib
import sys
from contextlib import suppress
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_domain_models_do_not_define_create_wrappers() -> None:
    violations = []
    for path in (BACKEND_ROOT / "domain").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for member in node.body:
                    if (
                        isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and member.name == "create"
                    ):
                        violations.append(
                            f"{path.relative_to(BACKEND_ROOT)}:{member.lineno}"
                        )
    assert not violations, violations


LAYER_NAMES = ("domain", "application", "infrastructure", "presentation")
ALLOWED_BACKEND_DIRECTORIES = {
    "domain",
    "application",
    "infrastructure",
    "presentation",
    "tests",
    "migrations",
    "config",
}
FILESYSTEM_METHODS = {
    "open",
    "read_text",
    "read_bytes",
    "write_text",
    "write_bytes",
    "iterdir",
    "glob",
    "rglob",
    "mkdir",
    "unlink",
    "rmdir",
    "touch",
    "is_file",
    "is_dir",
    "exists",
    "stat",
    "lstat",
    "readlink",
}
OS_IO_FUNCTIONS = {
    "getenv",
    "putenv",
    "unsetenv",
    "getcwd",
    "chdir",
    "listdir",
    "scandir",
    "makedirs",
    "remove",
    "rename",
    "renames",
    "replace",
    "access",
}


ALLOWED_DOMAIN_CONTEXT_FILES = {
    "__init__.py",
    "identifiers.py",
    "exceptions.py",
    "primitives.py",
    "value_objects.py",
    "entities.py",
    "repositories.py",
    "services.py",
}
ALLOWED_DOMAIN_INTERNAL_DEPENDENCIES: dict[str, set[str]] = {
    "__init__": set(),
    "identifiers": set(),
    "exceptions": set(),
    "primitives": {"exceptions"},
    "value_objects": {"exceptions", "identifiers", "primitives"},
    "entities": {"exceptions", "identifiers", "primitives", "value_objects"},
    "repositories": {
        "exceptions",
        "identifiers",
        "primitives",
        "value_objects",
        "entities",
    },
    "services": {
        "exceptions",
        "identifiers",
        "primitives",
        "value_objects",
        "entities",
        "repositories",
    },
}


ALLOWED_APPLICATION_CONTEXT_DEPENDENCIES: dict[str, set[str]] = {
    "chat": {"retrieval", "medicine"},
    "retrieval": {"medicine"},
    "attachment_import": {"indexing"},
    "indexing": {"medicine"},
    "medicine": set(),
}
EXTERNAL_ADAPTER_PACKAGES = {"llm", "intent", "morphology", "pmda_xml"}
INFRASTRUCTURE_ROOT_PAYLOAD_MODULES = {
    "evidence_mapping",
    "index_payloads",
    "json_payloads",
}
ALLOWED_INFRASTRUCTURE_PACKAGES = {
    "cli",
    "composition",
    "intent",
    "llm",
    "morphology",
    "package_insert_definitions",
    "persistence",
    "pmda_xml",
    "sources",
}
ALLOWED_INFRASTRUCTURE_ROOT_FILES = {
    "__init__.py",
    "evidence_mapping.py",
    "index_payloads.py",
    "json_payloads.py",
}


def _allowed_module(module: str, *, caller: str) -> bool:
    if module == "backend":
        return False
    # 公開IDは内部モデルや共通カタログを経由して業務実装を公開しない。
    caller_parts = caller.split(".")
    if (
        len(caller_parts) == 4
        and caller_parts[:2] == ["backend", "domain"]
        and caller_parts[-1] == "identifiers"
    ):
        return (
            module.split(".")[0] in sys.stdlib_module_names
            or module == "backend.domain.foundation.primitives.identifiers"
            or module.startswith("backend.domain.foundation.primitives.identifiers.")
        )
    module_parts = module.split(".")
    if (
        len(caller_parts) >= 3
        and caller_parts[:2] == ["backend", "domain"]
        and caller_parts[2] not in {"fixture", "inner_fixture"}
        and len(module_parts) >= 2
        and module_parts[:2] == ["backend", "domain"]
    ):
        if len(module_parts) < 3:
            return False
        caller_ctx = caller_parts[2]
        target_ctx = module_parts[2]
        if caller_ctx == "foundation":
            return target_ctx == "foundation"
        if caller_ctx == "shared":
            return target_ctx in {"shared", "foundation"}
        if target_ctx == "foundation":
            return len(module_parts) >= 4
        if target_ctx == "shared":
            if len(module_parts) < 4:
                return False
            if (
                len(caller_parts) == 4
                and caller_parts[3] in ALLOWED_DOMAIN_INTERNAL_DEPENDENCIES
            ):
                if module_parts[3] == "services":
                    return caller_parts[3] in {"entities", "repositories", "services"}
                return module_parts[3] in (
                    ALLOWED_DOMAIN_INTERNAL_DEPENDENCIES[caller_parts[3]]
                    | {caller_parts[3]}
                )
            return True
        if target_ctx == caller_ctx:
            if len(module_parts) < 4:
                return False
            if (
                len(caller_parts) == 4
                and caller_parts[3] in ALLOWED_DOMAIN_INTERNAL_DEPENDENCIES
            ):
                target_module = module_parts[3]
                if target_module != caller_parts[3]:
                    return (
                        target_module
                        in ALLOWED_DOMAIN_INTERNAL_DEPENDENCIES[caller_parts[3]]
                    )
            return True
        if len(module_parts) < 4 or module_parts[3] != "identifiers":
            return False
        if (
            len(caller_parts) == 4
            and caller_parts[3] in ALLOWED_DOMAIN_INTERNAL_DEPENDENCIES
        ):
            return (
                "identifiers" in ALLOWED_DOMAIN_INTERNAL_DEPENDENCIES[caller_parts[3]]
            )
        return True
    # Application層: コンテキスト間の有向パイプライン境界と *_models / *_contracts の依存制限。
    if (
        len(caller_parts) >= 3
        and caller_parts[:2] == ["backend", "application"]
        and caller_parts[2] != "fixture"
        and len(module_parts) >= 2
        and module_parts[:2] == ["backend", "application"]
    ):
        if len(module_parts) < 3:
            return False
        caller_ctx = caller_parts[2]
        target_ctx = module_parts[2]
        if caller_ctx != "chat" and target_ctx == "chat":
            return False
        if caller_ctx in ALLOWED_APPLICATION_CONTEXT_DEPENDENCIES:
            if (
                target_ctx != caller_ctx
                and target_ctx
                not in ALLOWED_APPLICATION_CONTEXT_DEPENDENCIES[caller_ctx]
            ):
                return False
            if len(module_parts) < 4:
                return False
        if len(caller_parts) >= 4:
            caller_mod = caller_parts[3]
            if caller_mod.endswith("_models") and (
                len(module_parts) < 4 or not module_parts[3].endswith("_models")
            ):
                return False
            if caller_mod.endswith("_contracts") and (
                len(module_parts) < 4
                or not (
                    module_parts[3].endswith("_models")
                    or module_parts[3].endswith("_contracts")
                )
            ):
                return False
    # Presentation層: 内部の依存順序（*_routes -> dependencies -> chat_service -> chat_dto_mapper -> *_models）を強制する。
    if (
        len(caller_parts) >= 3
        and caller_parts[:2] == ["backend", "presentation"]
        and caller_parts[2] != "fixture"
        and len(module_parts) >= 2
        and module_parts[:2] == ["backend", "presentation"]
    ):
        if len(module_parts) < 3:
            return False
        caller_mod = caller_parts[2]
        target_mod = module_parts[2]
        if caller_mod == target_mod:
            return True
        if caller_mod == "__init__":
            return target_mod.endswith("_routes")
        if caller_mod.endswith("_models"):
            return target_mod.endswith("_models")
        if caller_mod == "chat_dto_mapper":
            return target_mod.endswith("_models")
        if caller_mod == "chat_service":
            return target_mod == "chat_dto_mapper" or target_mod.endswith("_models")
        if caller_mod == "dependencies":
            return target_mod == "chat_service" or target_mod.endswith("_models")
        if caller_mod.endswith("_routes"):
            return target_mod in {
                "dependencies",
                "chat_service",
            } or target_mod.endswith("_models")
    # Infrastructure層: composition / cli への逆依存、persistence -> sources、
    # package_insert_definitions / root payload mappers -> 他adapter、外部技術Adapter間の相互依存を禁止する。
    if (
        len(caller_parts) >= 3
        and caller_parts[:2] == ["backend", "infrastructure"]
        and caller_parts[2] != "fixture"
        and len(module_parts) >= 2
        and module_parts[:2] == ["backend", "infrastructure"]
    ):
        if len(module_parts) < 3:
            return False
        caller_pkg = caller_parts[2]
        target_pkg = module_parts[2]
        if caller_pkg in INFRASTRUCTURE_ROOT_PAYLOAD_MODULES:
            return target_pkg == caller_pkg
        if caller_pkg == "package_insert_definitions":
            return target_pkg == "package_insert_definitions" and len(module_parts) >= 4
        if caller_pkg not in {"composition", "cli"} and target_pkg in {
            "composition",
            "cli",
        }:
            return False
        if caller_pkg == "composition" and target_pkg == "cli":
            return False
        if caller_pkg == "persistence":
            if target_pkg in {"sources", "llm", "intent", "morphology"}:
                return False
            if target_pkg == "pmda_xml":
                return (
                    caller
                    in {
                        "backend.infrastructure.persistence.generation_runtime",
                        "backend.infrastructure.persistence.registration_publisher",
                    }
                    and len(module_parts) >= 4
                    and module_parts[3] in {"decoder", "artifact_mapping"}
                )
        if caller_pkg in EXTERNAL_ADAPTER_PACKAGES:
            if target_pkg in {"persistence", "sources"}:
                return False
            if target_pkg in EXTERNAL_ADAPTER_PACKAGES and caller_pkg != target_pkg:
                return False
    caller_layer = next(
        (
            layer
            for layer in LAYER_NAMES
            if caller == f"backend.{layer}" or caller.startswith(f"backend.{layer}.")
        ),
        None,
    )
    if caller_layer == "presentation" and (
        module == "backend.main"
        or module.startswith("backend.main.")
        or module == "backend.migrations"
        or module.startswith("backend.migrations.")
    ):
        return False
    if caller_layer == "infrastructure" and (
        module == "backend.main" or module.startswith("backend.main.")
    ):
        return caller == "backend.infrastructure.composition.configured_probe"
    dependency_layer = next(
        (
            layer
            for layer in LAYER_NAMES
            if module == f"backend.{layer}" or module.startswith(f"backend.{layer}.")
        ),
        None,
    )
    if dependency_layer is not None:
        allowed_layers = {
            "domain": {"domain"},
            "application": {"domain", "application"},
            "infrastructure": {"domain", "application", "infrastructure"},
            "presentation": {"application", "presentation"},
        }
        return caller_layer is None or dependency_layer in allowed_layers[caller_layer]
    if caller_layer in {"domain", "application"}:
        return module.split(".")[0] in sys.stdlib_module_names
    return True


@pytest.mark.parametrize(
    ("source", "allowed"),
    [
        ("from dataclasses import dataclass\n", True),
        ("from ..foundation.primitives.identifiers import EntityStringId\n", True),
        ("from backend.domain.foundation.primitives import identifiers\n", True),
        ("from .primitives import SearchKeyword\n", False),
        ("from ..attachment.identifiers import DocumentId\n", False),
        ("from ..shared.services import normalize_match_text\n", False),
        (
            "from backend.infrastructure.package_insert_definitions.loader import PackageInsertDefinitions\n",
            False,
        ),
        ("from ..foundation.primitives.base import DomainPrimitive\n", False),
        (
            "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n"
            "    from .entities import SearchUnit\n",
            False,
        ),
    ],
)
def test_public_identifiers_only_depend_on_stdlib_and_id_base(
    source: str, allowed: bool
) -> None:
    violations = find_inner_layer_violations(
        source,
        module_name="backend.domain.retrieval.identifiers",
        filename="identifiers_fixture.py",
    )
    assert bool(violations) is not allowed, violations


def _qualified_name(node: ast.AST, aliases: dict[str, str]) -> str:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        prefix = _qualified_name(node.value, aliases)
        return f"{prefix}.{node.attr}" if prefix else ""
    if isinstance(node, ast.Call):
        return _qualified_name(node.func, aliases)
    return ""


def _outermost_attributes(root: ast.AST) -> list[ast.Attribute]:
    inner_values = {
        node.value for node in ast.walk(root) if isinstance(node, ast.Attribute)
    }
    return [
        node
        for node in ast.walk(root)
        if isinstance(node, ast.Attribute) and node not in inner_values
    ]


OUTPUT_RESPONSE_DTOS = {
    "backend.presentation.chat_models.ChatResponse",
    "backend.presentation.evidence_models.ChatSource",
    "backend.presentation.medicine_models.MedicineMatch",
}


def _annotation_names(
    node: ast.AST | None, aliases: dict[str, str], *, input_type: bool = False
) -> set[str]:
    if node is None:
        return set()
    if (
        input_type
        and isinstance(node, ast.Subscript)
        and _qualified_name(node.value, aliases).rsplit(".", 1)[-1] == "Callable"
    ):
        return set()  # Callback payloads are outgoing notifications, not input DTOs.
    names = set()
    if isinstance(node, (ast.Name, ast.Attribute)):
        names.add(_qualified_name(node, aliases))
    elif isinstance(node, ast.Constant) and isinstance(node.value, str):
        with suppress(SyntaxError):
            names.update(
                _annotation_names(
                    ast.parse(node.value, mode="eval"), aliases, input_type=input_type
                )
            )
    for child in ast.iter_child_nodes(node):
        names.update(_annotation_names(child, aliases, input_type=input_type))
    return names


def find_inner_layer_violations(
    source: str, *, module_name: str, filename: str
) -> list[str]:
    """全import（型確認用を含む）、型注釈、環境変数・ファイルIOを調べる。"""
    tree = ast.parse(source, filename=filename)
    violations: list[str] = []
    aliases: dict[str, str] = {}
    caller_is_inner = any(
        module_name == f"backend.{layer}" or module_name.startswith(f"backend.{layer}.")
        for layer in ("domain", "application")
    )

    def report(node: ast.AST, dependency: str) -> None:
        violations.append(f"{filename}:{getattr(node, 'lineno', 1)}: {dependency}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for imported in node.names:
                aliases[imported.asname or imported.name.split(".")[0]] = (
                    imported.name if imported.asname else imported.name.split(".")[0]
                )
                if not _allowed_module(imported.name, caller=module_name):
                    report(node, "import " + imported.name)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                package = module_name.split(".")[: -node.level]
                base = ".".join(package + ([base] if base else []))
            for imported in node.names:
                dependency = base + "." + imported.name if base else imported.name
                aliases[imported.asname or imported.name] = dependency
                if not _allowed_module(dependency, caller=module_name):
                    report(node, "import " + dependency)

    if module_name.startswith("backend.presentation."):
        for function in ast.walk(tree):
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            arguments = [
                *function.args.posonlyargs,
                *function.args.args,
                *function.args.kwonlyargs,
            ]
            if function.args.vararg is not None:
                arguments.append(function.args.vararg)
            if function.args.kwarg is not None:
                arguments.append(function.args.kwarg)
            inputs = set().union(
                *(
                    _annotation_names(arg.annotation, aliases, input_type=True)
                    for arg in arguments
                )
            )
            if not inputs.intersection(OUTPUT_RESPONSE_DTOS):
                continue
            targets = _annotation_names(function.returns, aliases)
            targets.update(
                _qualified_name(call.func, aliases)
                for call in ast.walk(function)
                if isinstance(call, ast.Call)
            )
            if any(target.startswith("backend.application.") for target in targets):
                report(function, "response DTO must not be rehydrated into Application")

    annotation_attr_ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Name, ast.Attribute)):
            dependency = _qualified_name(node, aliases)
            if caller_is_inner and (
                dependency == "os.environ" or dependency.startswith("os.environ.")
            ):
                report(node, "environment " + dependency)
        if isinstance(node, ast.Call):
            dependency = _qualified_name(node.func, aliases)
            method = dependency.rsplit(".", 1)[-1]
            if caller_is_inner and (
                method in FILESYSTEM_METHODS
                or (dependency.startswith("os.") and method in OS_IO_FUNCTIONS)
            ):
                report(node, "IO " + dependency)

        annotations: list[ast.AST] = []
        if isinstance(node, (ast.arg, ast.AnnAssign)) and node.annotation is not None:
            annotations.append(node.annotation)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.returns:
            annotations.append(node.returns)
        elif isinstance(node, ast.TypeAlias):
            annotations.append(node.value)
        for annotation in annotations:
            for reference in _outermost_attributes(annotation):
                annotation_attr_ids.add(id(reference))
                dependency = _qualified_name(reference, aliases)
                if (
                    dependency == "backend" or dependency.startswith("backend.")
                ) and not _allowed_module(dependency, caller=module_name):
                    report(node, "annotation " + dependency)
            for value in ast.walk(annotation):
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    try:
                        expression = ast.parse(value.value, mode="eval")
                    except SyntaxError:
                        continue
                    for reference in _outermost_attributes(expression):
                        dependency = _qualified_name(reference, aliases)
                        if dependency and not _allowed_module(
                            dependency, caller=module_name
                        ):
                            report(node, "annotation " + dependency)

    for reference in _outermost_attributes(tree):
        if id(reference) in annotation_attr_ids:
            continue
        dependency = _qualified_name(reference, aliases)
        if (
            dependency == "backend" or dependency.startswith("backend.")
        ) and not _allowed_module(dependency, caller=module_name):
            report(reference, "import " + dependency)

    return sorted(set(violations))


def test_inner_layers_are_technology_independent() -> None:
    violations: list[str] = []
    for layer in ("domain", "application"):
        directory = BACKEND_ROOT / layer
        assert directory.is_dir(), f"内側の層が存在しない: {directory}"
        files = sorted(directory.rglob("*.py"))
        assert files, f"検査対象がない: {directory}"
        for path in files:
            relative = path.relative_to(BACKEND_ROOT.parent)
            module_name = ".".join(relative.with_suffix("").parts)
            violations.extend(
                find_inner_layer_violations(
                    path.read_text(encoding="utf-8"),
                    module_name=module_name,
                    filename=relative.as_posix(),
                )
            )

    assert not violations, "内側の層に禁止依存がある:\n" + "\n".join(violations)


def test_four_layer_dependencies_are_valid_in_source() -> None:
    violations: list[str] = []
    for layer in LAYER_NAMES:
        directory = BACKEND_ROOT / layer
        assert directory.is_dir(), f"オニオン層が存在しない: {directory}"
        for path in sorted(directory.rglob("*.py")):
            relative = path.relative_to(BACKEND_ROOT.parent)
            module_name = ".".join(relative.with_suffix("").parts)
            violations.extend(
                find_inner_layer_violations(
                    path.read_text(encoding="utf-8"),
                    module_name=module_name,
                    filename=relative.as_posix(),
                )
            )

    assert not violations, "4層の依存方向に違反がある:\n" + "\n".join(violations)


def test_backend_root_contains_only_onion_layers_and_exceptions() -> None:
    generated = {
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".venv",
    }
    directories = {
        path.name
        for path in BACKEND_ROOT.iterdir()
        if path.is_dir() and path.name not in generated
    }

    assert directories == ALLOWED_BACKEND_DIRECTORIES


@pytest.mark.parametrize(
    ("module_name", "source", "expected_allowed"),
    [
        (
            "backend.application.fixture",
            "from backend.domain.attachment import entities\n",
            True,
        ),
        (
            "backend.infrastructure.fixture",
            "from backend.domain.medicine import repositories\n",
            True,
        ),
        (
            "backend.presentation.fixture",
            "from backend.application.chat import chat_models\n",
            True,
        ),
        (
            "backend.domain.fixture",
            "from backend.application.chat import chat_models\n",
            False,
        ),
        (
            "backend.application.fixture",
            "from backend.infrastructure import persistence\n",
            False,
        ),
        (
            "backend.presentation.fixture",
            "from backend.infrastructure import persistence\n",
            False,
        ),
    ],
)
def test_four_layer_dependency_directions(
    module_name: str, source: str, expected_allowed: bool
) -> None:
    violations = find_inner_layer_violations(
        source,
        module_name=module_name,
        filename="four_layer_fixture.py",
    )

    if expected_allowed:
        assert violations == []
    else:
        assert violations


def test_new_public_module_paths_are_importable_without_legacy_packages() -> None:
    public_modules = (
        "backend.presentation.chat_service",
        "backend.presentation.chat_routes",
        "backend.infrastructure.llm.provider_factory",
        "backend.infrastructure.composition.index_verifier",
        "backend.infrastructure.cli.build_search_index",
        "backend.infrastructure.cli.migrate_legacy_index",
    )
    for module in public_modules:
        importlib.import_module(module)

    for package in ("api", "composition", "llm", "cli"):
        assert not (BACKEND_ROOT / package).exists()


@pytest.mark.parametrize(
    ("source", "expected_diagnostic"),
    [
        pytest.param(
            "import pydantic as pd\n",
            ":1: import pydantic",
            id="direct_import",
        ),
        pytest.param(
            "from sqlalchemy import Row\n",
            ":1: import sqlalchemy.Row",
            id="from_import",
        ),
        pytest.param(
            "from ..infrastructure import persistence\n",
            ":1: import backend.infrastructure.persistence",
            id="relative_import",
        ),
        pytest.param(
            "from typing import TYPE_CHECKING\n"
            "if TYPE_CHECKING:\n"
            "    from backend.presentation import chat_routes\n",
            ":3: import backend.presentation.chat_routes",
            id="type_checking_import",
        ),
        pytest.param(
            "from backend.domain.retrieval.value_objects import IntentPolicy\n"
            "from backend.domain.retrieval.services import format_scoped_text\n",
            None,
            id="owned_domain_imports",
        ),
    ],
)
def test_dependency_check_detects_forbidden_imports(
    tmp_path: Path, source: str, expected_diagnostic: str | None
) -> None:
    path = tmp_path / "inner_fixture.py"
    path.write_text(source, encoding="utf-8")

    violations = find_inner_layer_violations(
        path.read_text(encoding="utf-8"),
        module_name="backend.domain.inner_fixture",
        filename=path.as_posix(),
    )

    if expected_diagnostic is None:
        assert violations == []
    else:
        assert violations == [path.as_posix() + expected_diagnostic]


def test_legacy_facades_are_not_required(tmp_path: Path) -> None:
    """旧配置facade（backend.storage等）に依存せず、公開入口が正常動作することを検証する。"""
    from backend.infrastructure.persistence.index_writer import SqlAlchemyIndexWriter
    from backend.infrastructure.persistence.sqlite_engine import create_sqlite_engine
    from backend.infrastructure.sources.file_index_source import FileIndexSourceReader
    from backend.main import create_app
    from backend.tests.storage_fixtures import write_structured_document
    from backend.tests.test_alembic_migrations import _migrate_database
    from fastapi.testclient import TestClient
    from sqlalchemy.engine import URL

    # 1. backend.main および CLI 入口が backend.storage を参照していないこと
    for file_path in (
        BACKEND_ROOT / "main.py",
        BACKEND_ROOT / "infrastructure" / "cli" / "build_search_index.py",
        BACKEND_ROOT / "infrastructure" / "cli" / "migrate_legacy_index.py",
    ):
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    assert "backend.storage" not in name.name
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert "backend.storage" not in module
                assert not (node.level == 1 and module.startswith("storage"))

    # 2. Smoke: 準備済み索引で backend.main:create_app が正常起動し各公開入口が応答すること
    structured = write_structured_document(tmp_path)
    index_path = tmp_path / "smoke.sqlite3"
    _migrate_database(index_path, structured)
    engine = create_sqlite_engine(
        URL.create("sqlite", database=index_path.as_posix()).render_as_string(
            hide_password=False
        )
    )
    try:
        SqlAlchemyIndexWriter(engine).replace(
            FileIndexSourceReader(structured).read_snapshot()
        )
    finally:
        engine.dispose()

    # v5 prepared index includes explicit initial registration, never startup DDL.
    import json

    from backend.infrastructure.persistence.attachment_import_store import (
        FileAttachmentImportStore,
    )
    from backend.infrastructure.persistence.registration_publisher import (
        RegistrationInput,
        SqliteRegistrationPublisher,
    )
    from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder
    from backend.tests.attachment_import_fixtures import xml_source

    raw = xml_source(
        "<AdverseEvents><Detail><Lang>頭痛に注意してください。記載0 記載1 記載2</Lang></Detail></AdverseEvents>"
    )
    raw = (
        raw.replace(b"000001", b"test")
        .replace(
            b"<PackageInsertNo>test</PackageInsertNo>",
            b"<PackageInsertNo>001</PackageInsertNo>",
        )
        .replace(b"111111111111", b"1234567A0000")
        .replace("製品A".encode(), "テスト薬".encode())
    )
    original = tmp_path / "source.xml"
    original.write_bytes(raw)
    document = structured / "test_001" / "document.json"
    units = structured / "test_001" / "search_units.jsonl"
    SqliteRegistrationPublisher(
        index_path,
        FileAttachmentImportStore(tmp_path / "imports"),
        allowed_roots=(tmp_path,),
    ).publish_inputs(
        (
            RegistrationInput(
                PmdaXmlDecoder().decode(raw),
                raw,
                (original, document, units),
                original,
                json.loads(document.read_bytes()),
            ),
        ),
        initial=True,
    )

    app = create_app(structured, index_path, import_directory=tmp_path / "imports")
    client = TestClient(app)
    with client:
        # /api プローブ
        res_api = client.get("/api")
        assert res_api.status_code == 200
        assert res_api.json() == {"status": "ok"}

        # /health
        res_health = client.get("/health")
        assert res_health.status_code == 200
        assert res_health.json()["status"] == "ok"

        # /api/medicines
        res_med = client.get("/api/medicines")
        assert res_med.status_code == 200
        assert len(res_med.json()["items"]) >= 1

        # /api/chat
        res_chat = client.post(
            "/api/chat",
            json={"message": "頭痛の薬", "product_yj_codes": ["999999999999"]},
        )
        assert res_chat.status_code == 200
        assert res_chat.json()["needs_clarification"] is True

        # /ws/chat
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_json({"type": "ping"})
            pong = ws.receive_json()
            assert pong == {"type": "pong"}


@pytest.mark.parametrize(
    "source",
    [
        "import backend.application.chat.chat_models\n",
        "from ...application.chat import chat_models\n",
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from backend.application.chat import chat_models\n",
    ],
)
def test_domain_cannot_depend_on_application(source: str) -> None:
    violations = find_inner_layer_violations(
        source,
        module_name="backend.domain.attachment.fixture",
        filename="domain_fixture.py",
    )
    assert violations
    assert all("backend.application" in message for message in violations)


@pytest.mark.parametrize(
    "module_name", ["backend.domain.fixture", "backend.application.fixture"]
)
def test_pure_owned_models_and_formatting_are_allowed(module_name: str) -> None:
    source = "from backend.domain.retrieval.value_objects import IntentPolicy\nfrom backend.domain.retrieval.services import section_code_sort_key\n"
    assert (
        find_inner_layer_violations(
            source, module_name=module_name, filename="shared_fixture.py"
        )
        == []
    )
    old_source = "from package_inserts.catalog_models import PackageInsertCatalog\nfrom package_inserts.text_formatting import section_code_sort_key\n"
    violations = find_inner_layer_violations(
        old_source, module_name=module_name, filename="old_shared_fixture.py"
    )
    assert len(violations) == 2
    assert all("package_inserts" in violation for violation in violations)


def test_application_can_depend_on_domain() -> None:
    assert (
        find_inner_layer_violations(
            "from backend.domain.attachment import entities\n",
            module_name="backend.application.fixture",
            filename="application_fixture.py",
        )
        == []
    )


def test_domain_models_have_explicit_primitive_entity_value_object_ownership() -> None:
    """ドメインの型定義を役割別の正本モジュールへ固定する。"""
    expected_modules = {
        "BaseString": "backend.domain.foundation.primitives.primitives",
        "BaseFiniteFloat": "backend.domain.foundation.primitives.primitives",
        "DocumentId": "backend.domain.attachment.identifiers",
        "ProductGroupId": "backend.domain.medicine.primitives",
        "Medicine": "backend.domain.medicine.entities",
        "IntentName": "backend.domain.retrieval.primitives",
        "PmdaUrl": "backend.domain.attachment.primitives",
        "Probability": "backend.domain.retrieval.primitives",
        "SearchKeyword": "backend.domain.retrieval.primitives",
        "SectionCode": "backend.domain.attachment.primitives",
        "SearchUnitId": "backend.domain.retrieval.identifiers",
        "YjCode": "backend.domain.medicine.identifiers",
        "JsonValue": "backend.domain.foundation.json_types",
        "DetectionSource": "backend.domain.retrieval.primitives",
        "DocumentRevision": "backend.domain.retrieval.value_objects",
        "ResolvedMedicine": "backend.application.medicine.product_models",
        "SearchCriteria": "backend.domain.retrieval.value_objects",
        "IntentCandidate": "backend.domain.retrieval.value_objects",
        "IntentSelection": "backend.domain.retrieval.value_objects",
        "EvidenceReference": "backend.domain.retrieval.value_objects",
        "EvidenceSection": "backend.domain.retrieval.value_objects",
        "EvidenceColumns": "backend.domain.retrieval.value_objects",
        "RegisteredMedicine": "backend.application.medicine.product_models",
        "Evidence": "backend.domain.retrieval.value_objects",
        "ProductIdentityReason": "backend.domain.retrieval.primitives",
        "QuestionProductName": "backend.domain.retrieval.primitives",
        "IntentKeywordText": "backend.domain.retrieval.primitives",
        "ProductQuestion": "backend.domain.retrieval.value_objects",
        "merge_evidence": "backend.domain.retrieval.services",
        "recognize_product_questions": "backend.domain.retrieval.services",
        "product_identity_reason": "backend.domain.retrieval.services",
        "build_keyword_search_criteria": "backend.domain.retrieval.services",
        "katakana_to_hiragana": "backend.domain.shared.services",
        "RegisteredMedicineReader": "backend.application.medicine.product_contracts",
        "EvidenceRepository": "backend.domain.retrieval.repositories",
        "MedicineCatalog": "backend.application.medicine.product_catalog",
        "DomainException": "backend.domain.foundation.exceptions",
        "DomainValidationError": "backend.domain.foundation.exceptions",
    }

    for name, module_name in expected_modules.items():
        module = importlib.import_module(module_name)
        value = getattr(module, name)
        if name == "JsonValue":
            assert value is not None
            continue
        assert getattr(value, "__module__", module_name) == module_name, (
            f"{name} の正本が {module_name} に定義されていない"
        )
    assert not (BACKEND_ROOT / "domain" / "retrieval" / "product_identity.py").exists()


def test_domain_has_no_compatibility_facades() -> None:
    """旧ドメインFacadeを残さず、正本だけを公開する。"""
    removed_paths = tuple(
        BACKEND_ROOT / "domain" / directory
        for directory in (
            "entities",
            "exceptions",
            "primitives",
            "repositories",
            "services",
            "value_objects",
        )
    )
    assert all(not path.exists() for path in removed_paths)


def test_public_modules_and_api_work_without_legacy_packages_in_subprocess(
    tmp_path: Path,
) -> None:
    import os
    import subprocess

    from backend.tests.storage_fixtures import (
        build_document_store,
        write_structured_document,
    )

    structured = write_structured_document(tmp_path)
    index_path = tmp_path / "isolated.sqlite3"
    build_document_store(structured, index_path)
    from backend.tests.registration_runtime_fixtures import (
        register_synthetic_prepared_index,
    )

    register_synthetic_prepared_index(structured, index_path)
    for package in ("chat", "retrieval", "medicines", "storage", "jev"):
        assert not (BACKEND_ROOT / package).exists()
    environment = dict(os.environ)
    environment.update(
        PYTHON_DOTENV_DISABLED="1",
        TYPESAFE_API_KEY="",
        JEV_API_KEY="",
        OPENAI_API_KEY="",
        GEMINI_API_KEY="",
        GOOGLE_API_KEY="",
    )
    code = """
import importlib, sys
from pathlib import Path
from backend.main import create_app
from fastapi.testclient import TestClient
for module in ("backend.presentation.chat_service", "backend.infrastructure.cli.build_search_index", "backend.infrastructure.cli.migrate_legacy_index"):
    importlib.import_module(module)
with TestClient(create_app(Path(sys.argv[1]), Path(sys.argv[2]))) as client:
    assert client.get("/api").json() == {"status": "ok"}
    assert client.get("/health").json()["status"] == "ok"
    assert len(client.get("/api/medicines").json()["items"]) == 1
    response = client.post("/api/chat", json={"message": "頭痛", "product_yj_codes": ["999999999999"]})
    assert response.status_code == 200 and response.json()["needs_clarification"]
    with client.websocket_connect("/api/ws") as socket:
        socket.send_json({"type": "ping"})
        assert socket.receive_json() == {"type": "pong"}
print("canonical modules and API smoke passed")
"""
    process = subprocess.run(
        [sys.executable, "-c", code, str(structured), str(index_path)],
        cwd=BACKEND_ROOT.parent,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert process.returncode == 0, process.stdout + process.stderr
    assert "canonical modules and API smoke passed" in process.stdout


@pytest.mark.parametrize(
    ("module_name", "source", "line", "dependency"),
    [
        (
            "backend.domain",
            "import backend.application.chat.chat_models\n",
            1,
            "import backend.application.chat.chat_models",
        ),
        (
            "backend.application.fixture",
            "from backend.infrastructure import persistence\n",
            1,
            "import backend.infrastructure.persistence",
        ),
        (
            "backend.application.fixture",
            "from ..presentation import chat_models\n",
            1,
            "import backend.presentation.chat_models",
        ),
        (
            "backend.application.fixture",
            "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import typesafe_sdk\n",
            3,
            "import typesafe_sdk",
        ),
        (
            "backend.application.fixture",
            "from backend.infrastructure.package_insert_definitions.loader import get_package_insert_definitions\n",
            1,
            "import backend.infrastructure.package_insert_definitions.loader.get_package_insert_definitions",
        ),
        (
            "backend.domain.fixture",
            "from pathlib import Path\nPath('fixture').read_text()\n",
            2,
            "IO pathlib.Path.read_text",
        ),
        (
            "backend.domain.fixture",
            "import os\nvalue = os.getenv('fixture')\n",
            2,
            "IO os.getenv",
        ),
        (
            "backend.domain.retrieval.primitives",
            "from .value_objects import SearchCriteria\n",
            1,
            "import backend.domain.retrieval.value_objects.SearchCriteria",
        ),
        (
            "backend.domain.retrieval.value_objects",
            "from .entities import SearchUnit\n",
            1,
            "import backend.domain.retrieval.entities.SearchUnit",
        ),
        (
            "backend.domain.retrieval.entities",
            "from .services import merge_evidence\n",
            1,
            "import backend.domain.retrieval.services.merge_evidence",
        ),
        (
            "backend.application.medicine.suggestions",
            "from ..chat.answer_preparation import prepare_reply\n",
            1,
            "import backend.application.chat.answer_preparation.prepare_reply",
        ),
        (
            "backend.application.retrieval.retrieval_models",
            "from .retrieve_evidence import retrieve_evidence\n",
            1,
            "import backend.application.retrieval.retrieve_evidence.retrieve_evidence",
        ),
        (
            "backend.application.retrieval.intent_contracts",
            "from .jev_detector import detect_jev_criteria\n",
            1,
            "import backend.application.retrieval.jev_detector.detect_jev_criteria",
        ),
        (
            "backend.presentation.search_routes",
            "from ..domain.retrieval.repositories import EvidenceRepository\n",
            1,
            "import backend.domain.retrieval.repositories.EvidenceRepository",
        ),
        (
            "backend.infrastructure.persistence.registration_publisher",
            "from ..composition.index_verifier import verify_schema_readiness\n",
            1,
            "import backend.infrastructure.composition.index_verifier.verify_schema_readiness",
        ),
        (
            "backend.domain.retrieval.primitives",
            "from . import value_objects\n",
            1,
            "import backend.domain.retrieval.value_objects",
        ),
        (
            "backend.application.medicine.suggestions",
            "from backend.application.chat import answer_question\n",
            1,
            "import backend.application.chat.answer_question",
        ),
        (
            "backend.application.retrieval.retrieval_models",
            "from . import retrieve_evidence\n",
            1,
            "import backend.application.retrieval.retrieve_evidence",
        ),
        (
            "backend.application.retrieval.intent_contracts",
            "from . import jev_detector\n",
            1,
            "import backend.application.retrieval.jev_detector",
        ),
        (
            "backend.presentation.search_routes",
            "from ..domain.retrieval import repositories\n",
            1,
            "import backend.domain.retrieval.repositories",
        ),
        (
            "backend.infrastructure.persistence.registration_publisher",
            "from ..composition import index_verifier\n",
            1,
            "import backend.infrastructure.composition.index_verifier",
        ),
        (
            "backend.presentation.request_logging",
            "from ..domain.retrieval.value_objects import Evidence\n",
            1,
            "import backend.domain.retrieval.value_objects.Evidence",
        ),
        (
            "backend.presentation.request_logging",
            'def f(x: "backend.domain.retrieval.value_objects.Evidence") -> None:\n    pass\n',
            1,
            "annotation backend.domain.retrieval.value_objects.Evidence",
        ),
        (
            "backend.presentation.chat_service",
            'def f(x: "backend.domain.medicine.entities.Medicine") -> None:\n    pass\n',
            1,
            "annotation backend.domain.medicine.entities.Medicine",
        ),
        (
            "backend.domain.retrieval.services",
            "from ..medicine.entities import Medicine\n",
            1,
            "import backend.domain.medicine.entities.Medicine",
        ),
        (
            "backend.domain.retrieval.services",
            'def f(x: "backend.domain.medicine.entities.Medicine") -> None:\n    pass\n',
            1,
            "annotation backend.domain.medicine.entities.Medicine",
        ),
        (
            "backend.domain.foundation.primitives.base",
            "from ...retrieval.primitives import SearchKeyword\n",
            1,
            "import backend.domain.retrieval.primitives.SearchKeyword",
        ),
        (
            "backend.domain.shared.services",
            'def f(x: "backend.domain.retrieval.primitives.SearchKeyword") -> None:\n    pass\n',
            1,
            "annotation backend.domain.retrieval.primitives.SearchKeyword",
        ),
        (
            "backend.domain.retrieval.primitives",
            "from ..shared.services import normalize_match_text\n",
            1,
            "import backend.domain.shared.services.normalize_match_text",
        ),
        (
            "backend.application.medicine.autocomplete",
            "from ..retrieval.snapshot_contracts import RetrievalSnapshotProvider\n",
            1,
            "import backend.application.retrieval.snapshot_contracts.RetrievalSnapshotProvider",
        ),
        (
            "backend.application.medicine.autocomplete",
            'def f(x: "backend.application.retrieval.snapshot_contracts.RetrievalSnapshotProvider") -> None:\n    pass\n',
            1,
            "annotation backend.application.retrieval.snapshot_contracts.RetrievalSnapshotProvider",
        ),
        (
            "backend.application.retrieval.retrieve_evidence",
            "from ..indexing.attachment_projection import project_attachment\n",
            1,
            "import backend.application.indexing.attachment_projection.project_attachment",
        ),
        (
            "backend.infrastructure.persistence.registration_publisher",
            "from ..sources.file_index_source import FileIndexSourceReader\n",
            1,
            "import backend.infrastructure.sources.file_index_source.FileIndexSourceReader",
        ),
        (
            "backend.infrastructure.persistence.registration_publisher",
            'def f(x: "backend.infrastructure.sources.file_index_source.FileIndexSourceReader") -> None:\n    pass\n',
            1,
            "annotation backend.infrastructure.sources.file_index_source.FileIndexSourceReader",
        ),
        (
            "backend.infrastructure.llm.provider_factory",
            'def f(x: "backend.infrastructure.intent.jev_intent_detector.JevIntentDetector") -> None:\n    pass\n',
            1,
            "annotation backend.infrastructure.intent.jev_intent_detector.JevIntentDetector",
        ),
        (
            "backend.presentation.search_routes",
            "import backend\n",
            1,
            "import backend",
        ),
        (
            "backend.domain.retrieval.primitives",
            "import backend.domain.retrieval.exceptions\nx: backend.domain.retrieval.value_objects.SearchCriteria\n",
            2,
            "annotation backend.domain.retrieval.value_objects.SearchCriteria",
        ),
        (
            "backend.domain.retrieval.primitives",
            "import backend.domain.retrieval.exceptions\nx = backend.domain.retrieval.value_objects.SearchCriteria\n",
            2,
            "import backend.domain.retrieval.value_objects.SearchCriteria",
        ),
        (
            "backend.presentation.chat_service",
            "from ..domain.retrieval.repositories import EvidenceRepository\n",
            1,
            "import backend.domain.retrieval.repositories.EvidenceRepository",
        ),
        (
            "backend.presentation.evidence_models",
            "from ..domain.retrieval.primitives import DetectionSource\n",
            1,
            "import backend.domain.retrieval.primitives.DetectionSource",
        ),
        (
            "backend.presentation.chat_models",
            "from .chat_service import AppChatService\n",
            1,
            "import backend.presentation.chat_service.AppChatService",
        ),
        (
            "backend.presentation.chat_dto_mapper",
            "from .chat_service import AppChatService\n",
            1,
            "import backend.presentation.chat_service.AppChatService",
        ),
        (
            "backend.presentation.chat_service",
            "from .dependencies import get_chat_service\n",
            1,
            "import backend.presentation.dependencies.get_chat_service",
        ),
        (
            "backend.presentation.dependencies",
            "from .chat_routes import router\n",
            1,
            "import backend.presentation.chat_routes.router",
        ),
        (
            "backend.presentation.chat_routes",
            "from .search_routes import router\n",
            1,
            "import backend.presentation.search_routes.router",
        ),
        (
            "backend.infrastructure.package_insert_definitions.loader",
            "from ..intent.definition_settings import JevClassificationSettings\n",
            1,
            "import backend.infrastructure.intent.definition_settings.JevClassificationSettings",
        ),
        (
            "backend.infrastructure.evidence_mapping",
            "from .persistence.evidence_reader import SqlAlchemyEvidenceReader\n",
            1,
            "import backend.infrastructure.persistence.evidence_reader.SqlAlchemyEvidenceReader",
        ),
        (
            "backend.infrastructure.persistence.attachment_import_store",
            "from ..pmda_xml.artifact_mapping import result_from_dict\n",
            1,
            "import backend.infrastructure.pmda_xml.artifact_mapping.result_from_dict",
        ),
    ],
)
def test_layer_specific_forbidden_dependencies_report_location(
    module_name: str, source: str, line: int, dependency: str
) -> None:
    violations = find_inner_layer_violations(
        source, module_name=module_name, filename="fixture.py"
    )
    assert f"fixture.py:{line}: {dependency}" in violations


def test_import_linter_contracts_detect_submodule_violations() -> None:
    """pyproject.toml の全 Import Linter 契約が配下モジュール間の違反を検出できることを検証する。"""
    import copy

    import grimp
    from importlinter.application.use_cases import (
        _register_contract_types,
        read_user_options,
    )
    from importlinter.configuration import configure
    from importlinter.domain.contract import registry

    configure()
    user_options = read_user_options(
        config_filename=str(BACKEND_ROOT / "pyproject.toml")
    )
    _register_contract_types(user_options)
    base_graph = grimp.build_graph("backend")
    contracts = {
        c["name"]: registry.get_contract_class(c["type"])(
            name=c["name"],
            session_options=user_options.session_options,
            contract_options=c,
        )
        for c in user_options.contracts_options
    }

    synthetic_violations = (
        (
            "Domain does not depend on outer layers",
            "backend.domain.retrieval.services",
            "backend.application.chat.answer_question",
        ),
        (
            "Application does not depend on outer layers",
            "backend.application.retrieval.retrieve_evidence",
            "backend.infrastructure.persistence.sqlite_evidence_repository",
        ),
        (
            "Presentation does not depend on infrastructure",
            "backend.presentation.search_routes",
            "backend.infrastructure.persistence.sqlite_evidence_repository",
        ),
        (
            "Infrastructure does not depend on presentation",
            "backend.infrastructure.persistence.sqlite_evidence_repository",
            "backend.presentation.search_routes",
        ),
        (
            "Config does not depend on layers",
            "backend.config.runtime_settings",
            "backend.domain.retrieval.services",
        ),
        (
            "Presentation does not depend on domain",
            "backend.presentation.search_routes",
            "backend.domain.retrieval.services",
        ),
        (
            "Presentation does not depend on domain",
            "backend.presentation.search_routes",
            "backend.domain.retrieval.value_objects",
        ),
        (
            "Presentation does not depend on domain",
            "backend.presentation.chat_service",
            "backend.domain.retrieval.repositories",
        ),
        (
            "Presentation does not depend on domain",
            "backend.presentation.evidence_models",
            "backend.domain.retrieval.primitives",
        ),
        (
            "Presentation does not depend on domain",
            "backend.presentation.chat_dto_mapper",
            "backend.domain.retrieval.value_objects",
        ),
        (
            "Presentation does not depend on domain",
            "backend.presentation.attachment_import_routes",
            "backend.domain.foundation.exceptions",
        ),
        (
            "Presentation modules follow internal dependency hierarchy",
            "backend.presentation.chat_models",
            "backend.presentation.chat_service",
        ),
        (
            "Presentation modules follow internal dependency hierarchy",
            "backend.presentation.chat_dto_mapper",
            "backend.presentation.chat_service",
        ),
        (
            "Presentation modules follow internal dependency hierarchy",
            "backend.presentation.chat_service",
            "backend.presentation.dependencies",
        ),
        (
            "Presentation modules follow internal dependency hierarchy",
            "backend.presentation.dependencies",
            "backend.presentation.chat_routes",
        ),
        (
            "Presentation modules follow internal dependency hierarchy",
            "backend.presentation.chat_routes",
            "backend.presentation.search_routes",
        ),
        (
            "Non-chat application contexts do not depend on chat",
            "backend.application.retrieval.retrieve_evidence",
            "backend.application.chat.answer_question",
        ),
        (
            "Non-chat application contexts do not depend on chat",
            "backend.application.attachment_import.import_document",
            "backend.application.chat.answer_question",
        ),
        (
            "Medicine catalogue does not depend on retrieval use cases",
            "backend.application.medicine.autocomplete",
            "backend.application.retrieval.snapshot_contracts",
        ),
        (
            "Medicine catalogue does not depend on retrieval use cases",
            "backend.application.medicine.autocomplete",
            "backend.application.indexing.attachment_projection",
        ),
        (
            "Application contexts follow directed pipeline boundaries",
            "backend.application.retrieval.retrieve_evidence",
            "backend.application.indexing.attachment_projection",
        ),
        (
            "Application contexts follow directed pipeline boundaries",
            "backend.application.attachment_import.import_document",
            "backend.application.retrieval.retrieve_evidence",
        ),
        (
            "Persistence does not depend on input sources",
            "backend.infrastructure.persistence.registration_publisher",
            "backend.infrastructure.sources.file_index_source",
        ),
        (
            "Persistence does not depend on non-XML technology adapters and isolates XML fallback",
            "backend.infrastructure.persistence.attachment_import_store",
            "backend.infrastructure.pmda_xml.artifact_mapping",
        ),
        (
            "Persistence does not depend on non-XML technology adapters and isolates XML fallback",
            "backend.infrastructure.persistence.evidence_reader",
            "backend.infrastructure.intent.jev_classifier",
        ),
        (
            "Infrastructure adapters do not depend on composition or CLI",
            "backend.infrastructure.persistence.registration_publisher",
            "backend.infrastructure.composition.index_verifier",
        ),
        (
            "Package insert definitions do not depend on other infrastructure adapters",
            "backend.infrastructure.package_insert_definitions.loader",
            "backend.infrastructure.intent.definition_settings",
        ),
        (
            "Infrastructure payload mappers do not depend on adapter packages",
            "backend.infrastructure.evidence_mapping",
            "backend.infrastructure.persistence.evidence_reader",
        ),
        (
            "External technology adapters are independent",
            "backend.infrastructure.llm.provider_factory",
            "backend.infrastructure.intent.jev_intent_detector",
        ),
        (
            "Domain contexts are independent",
            "backend.domain.retrieval.services",
            "backend.domain.medicine.entities",
        ),
        (
            "Foundation does not depend on business vocabulary",
            "backend.domain.foundation.primitives.base",
            "backend.domain.retrieval.primitives",
        ),
        (
            "Shared does not depend on business contexts",
            "backend.domain.shared.services",
            "backend.domain.retrieval.primitives",
        ),
        (
            "Public identifiers do not expose business implementation",
            "backend.domain.retrieval.identifiers",
            "backend.domain.retrieval.primitives",
        ),
        (
            "Domain primitives do not depend on value objects, entities, repositories, or services",
            "backend.domain.retrieval.primitives",
            "backend.domain.retrieval.value_objects",
        ),
        (
            "Domain value objects do not depend on entities, repositories, or services",
            "backend.domain.retrieval.value_objects",
            "backend.domain.retrieval.entities",
        ),
        (
            "Domain entities do not depend on repositories or services",
            "backend.domain.retrieval.entities",
            "backend.domain.retrieval.services",
        ),
        (
            "Domain repositories do not depend on services",
            "backend.domain.retrieval.repositories",
            "backend.domain.retrieval.services",
        ),
    )

    assert {name for name, _, _ in synthetic_violations} == set(contracts)
    for contract_name, importer, imported in synthetic_violations:
        graph = copy.deepcopy(base_graph)
        graph.add_import(importer=importer, imported=imported)
        check = contracts[contract_name].check(graph, verbose=False)
        assert not check.kept, (
            f"{contract_name} が {importer} -> {imported} の違反を検出できていない"
        )


def test_tracked_production_packages_define_init_py() -> None:
    """Import Linter が追跡する本番パッケージ（4層＋config）で __init__.py の欠落による検査漏れを防ぐ。"""
    generated = {
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".venv",
    }
    tracked_roots = (*LAYER_NAMES, "config")
    missing: list[str] = []

    for root_name in tracked_roots:
        root_dir = BACKEND_ROOT / root_name
        for directory in sorted((root_dir, *root_dir.rglob("*"))):
            if not directory.is_dir():
                continue
            if any(
                part in generated for part in directory.relative_to(BACKEND_ROOT).parts
            ):
                continue
            if (
                any(directory.glob("*.py"))
                and not (directory / "__init__.py").is_file()
            ):
                missing.append(directory.relative_to(BACKEND_ROOT).as_posix())

    assert not missing, (
        "Import Linter の追跡対象パッケージに __init__.py がありません:\n"
        + "\n".join(missing)
    )


def test_infrastructure_root_contains_only_allowed_packages_and_payload_modules() -> (
    None
):
    """backend/infrastructure 直下には許可されたサブパッケージと純粋ペイロード変換モジュールのみを配置する。"""
    generated = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
    infra_root = BACKEND_ROOT / "infrastructure"
    packages = {
        child.name
        for child in infra_root.iterdir()
        if child.is_dir() and child.name not in generated
    }
    py_files = {
        child.name
        for child in infra_root.iterdir()
        if child.is_file() and child.suffix == ".py"
    }
    assert packages == ALLOWED_INFRASTRUCTURE_PACKAGES
    assert py_files == ALLOWED_INFRASTRUCTURE_ROOT_FILES


def test_domain_context_files_follow_canonical_flat_structure() -> None:
    """各ドメインコンテキスト直下に責務別の正本ファイル以外のファイルやサブディレクトリを追加させない。"""
    generated = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
    domain_root = BACKEND_ROOT / "domain"
    violations: list[str] = []

    for context_dir in sorted(domain_root.iterdir()):
        if context_dir.name in generated:
            continue
        if not context_dir.is_dir():
            if context_dir.name != "__init__.py":
                violations.append(
                    f"{context_dir.relative_to(BACKEND_ROOT)}: domain直下にはコンテキストパッケージのみ配置してください"
                )
            continue
        if context_dir.name == "foundation":
            continue
        for child in sorted(context_dir.iterdir()):
            if child.name in generated:
                continue
            if child.is_dir():
                violations.append(
                    f"{child.relative_to(BACKEND_ROOT)}: サブディレクトリは作成せず直下の正本モジュールに配置してください"
                )
            elif (
                child.suffix == ".py" and child.name not in ALLOWED_DOMAIN_CONTEXT_FILES
            ):
                allowed_list = ", ".join(sorted(ALLOWED_DOMAIN_CONTEXT_FILES))
                violations.append(
                    f"{child.relative_to(BACKEND_ROOT)}: 許可されたファイル名 ({allowed_list}) 以外は配置できません"
                )

    assert not violations, "ドメインコンテキストの構成違反:\n" + "\n".join(violations)


def test_each_domain_context_exposes_exactly_one_public_identifier() -> None:
    """各ドメインコンテキストの identifiers.py は1つの公開IDクラスのみを定義する（1 Domain = 1 ID）。"""
    expected = {
        "attachment": ["DocumentId"],
        "medicine": ["YjCode"],
        "retrieval": ["SearchUnitId"],
    }
    actual: dict[str, list[str]] = {}
    for context_name in sorted(expected):
        identifiers_file = BACKEND_ROOT / "domain" / context_name / "identifiers.py"
        tree = ast.parse(identifiers_file.read_text(encoding="utf-8"))
        actual[context_name] = [
            node.name for node in tree.body if isinstance(node, ast.ClassDef)
        ]
    assert actual == expected


def test_domain_dataclasses_are_frozen_and_use_immutable_collections() -> None:
    """ドメイン内の全 @dataclass が frozen=True かつミュータブルな list/dict/set をフィールドに持たないことを検証する。"""
    domain_root = BACKEND_ROOT / "domain"
    mutable_types = {"list", "dict", "set", "List", "Dict", "Set"}
    violations: list[str] = []

    for path in sorted(domain_root.rglob("*.py")):
        rel = path.relative_to(BACKEND_ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for dec in node.decorator_list:
                is_dataclass = (
                    isinstance(dec, ast.Name) and dec.id == "dataclass"
                ) or (
                    isinstance(dec, ast.Call)
                    and isinstance(dec.func, ast.Name)
                    and dec.func.id == "dataclass"
                )
                if not is_dataclass:
                    continue
                is_frozen = False
                if isinstance(dec, ast.Call):
                    for kw in dec.keywords:
                        if (
                            kw.arg == "frozen"
                            and isinstance(kw.value, ast.Constant)
                            and kw.value.value is True
                        ):
                            is_frozen = True
                if not is_frozen:
                    violations.append(
                        f"{rel}:{node.lineno}: {node.name} には @dataclass(frozen=True) を指定してください"
                    )
                for item in node.body:
                    if (
                        isinstance(item, ast.AnnAssign)
                        and item.annotation is not None
                        and isinstance(item.target, ast.Name)
                    ):
                        for sub in ast.walk(item.annotation):
                            if isinstance(sub, ast.Name) and sub.id in mutable_types:
                                violations.append(
                                    f"{rel}:{item.lineno}: {node.name}.{item.target.id} にミュータブルな {sub.id} は使用せず tuple / frozenset / ImmutableMapping を使用してください"
                                )

    assert not violations, "ドメインモデルの不変性違反:\n" + "\n".join(violations)


def test_response_dto_boundaries_in_presentation() -> None:
    violations = []
    for path in sorted((BACKEND_ROOT / "presentation").rglob("*.py")):
        relative = path.relative_to(BACKEND_ROOT.parent)
        violations.extend(
            find_inner_layer_violations(
                path.read_text(encoding="utf-8"),
                module_name=".".join(relative.with_suffix("").parts),
                filename=relative.as_posix(),
            )
        )
    assert not violations, "\n".join(violations)


@pytest.mark.parametrize(
    "source, forbidden",
    [
        (
            "from .chat_models import ChatResponse as Public\n"
            "from ..application.chat.chat_models import ChatResponse as Result\n"
            "def convert(value: Public) -> Result: ...\n",
            True,
        ),
        (
            "from . import evidence_models as api\n"
            "from ..application.retrieval import retrieval_models as app\n"
            "def convert(*, values: 'list[api.ChatSource]') -> 'list[app.Evidence]': ...\n",
            True,
        ),
        (
            "from .medicine_models import MedicineMatch as Public\n"
            "from ..application.medicine.product_models import ResolvedMedicine\n"
            "def convert(value: Public): return ResolvedMedicine()\n",
            True,
        ),
        (
            "from .chat_models import ChatMessage as Public\n"
            "from ..application.chat.chat_models import ChatMessage as Input\n"
            "def convert(value: Public) -> Input: ...\n",
            False,
        ),
        (
            "from .chat_models import ChatResponse as Public\n"
            "from ..application.chat.chat_models import ChatResponse as Result\n"
            "def convert(value: Result) -> Public: ...\n",
            False,
        ),
        (
            "from .evidence_models import ChatSource\n"
            "def publish(sources: list[ChatSource]) -> None: ...\n",
            False,
        ),
        (
            "from collections.abc import Callable, Awaitable\n"
            "from .evidence_models import ChatSource\n"
            "from ..application.chat.chat_models import ChatResponse\n"
            "def prepare(notify: Callable[[list[ChatSource]], Awaitable[None]]) -> ChatResponse: ...\n",
            False,
        ),
    ],
)
def test_response_dto_rule_detects_reverse_conversions(source, forbidden) -> None:
    violations = find_inner_layer_violations(
        source, module_name="backend.presentation.fixture", filename="fixture.py"
    )
    detected = any("response DTO" in violation for violation in violations)
    assert detected is forbidden
