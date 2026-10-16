"""内側の層が外部技術や実IOに依存しないことを検証する。"""

from __future__ import annotations

import ast
import importlib
import sys
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


def _allowed_module(module: str, *, caller: str) -> bool:
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
    caller_layer = next(
        (
            layer
            for layer in LAYER_NAMES
            if caller == f"backend.{layer}" or caller.startswith(f"backend.{layer}.")
        ),
        None,
    )
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
            "presentation": {"domain", "application", "presentation"},
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
        return _qualified_name(node.value, aliases) + "." + node.attr
    if isinstance(node, ast.Call):
        return _qualified_name(node.func, aliases)
    return ""


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
                dependency = base + "." + imported.name
                aliases[imported.asname or imported.name] = dependency
                if not _allowed_module(
                    base, caller=module_name
                ) and not _allowed_module(dependency, caller=module_name):
                    report(node, "import " + dependency)

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
            for value in ast.walk(annotation):
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    try:
                        expression = ast.parse(value.value, mode="eval")
                    except SyntaxError:
                        continue
                    for reference in ast.walk(expression):
                        if isinstance(reference, ast.Attribute):
                            dependency = _qualified_name(reference, aliases)
                            if not _allowed_module(dependency, caller=module_name):
                                report(node, "annotation " + dependency)

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

    from backend.infrastructure.persistence.registration_publisher import (
        RegistrationInput,
        SqliteRegistrationPublisher,
    )
    from backend.infrastructure.pmda_xml.decoder import PmdaXmlDecoder
    from backend.infrastructure.sources.attachment_import_store import (
        FileAttachmentImportStore,
    )
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
        "JsonValue": "backend.domain.json_types",
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
        "merge_evidence": "backend.domain.retrieval.services",
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
    ],
)
def test_layer_specific_forbidden_dependencies_report_location(
    module_name: str, source: str, line: int, dependency: str
) -> None:
    violations = find_inner_layer_violations(
        source, module_name=module_name, filename="fixture.py"
    )
    assert f"fixture.py:{line}: {dependency}" in violations
