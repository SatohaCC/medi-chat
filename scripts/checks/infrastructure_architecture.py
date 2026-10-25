"""Static Infrastructure architecture and boundary checker.

Never imports or executes inspected code; uses AST analysis only.
Enforces DDD/Onion layout, naming, imports, dependencies, public contracts,
cycles, dynamic bypasses, and Repository/ORM/Core responsibilities.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import tomllib
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, order=True)
class Finding:
    path: str
    line: int
    rule: str
    message: str


GENERIC_NAMES = frozenset(
    {
        "utils.py",
        "helpers.py",
        "common.py",
        "base.py",
        "models.py",
        "interfaces.py",
        "service.py",
    }
)

PERSISTENCE_ROLE_PATTERNS = {
    "schemas": re.compile(r"^(.+_tables|metadata)\.py$"),
    "stores": re.compile(r"^postgres_.+_store\.py$"),
    "queries": re.compile(
        r"^(postgres_.+_(query_reader|snapshot_provider)|trigram_search)\.py$"
    ),
    "registration": re.compile(
        r"^(postgres_.+_(publisher|replay_reader)|registration_.+|revision_selection)\.py$"
    ),
    "records": re.compile(r"^postgres_.+_records\.py$"),
    "mappings": re.compile(r"^.+_mapping\.py$"),
    "runtime": re.compile(r"^(postgres_.+|.+_workers)\.py$"),
    "maintenance": re.compile(r"^postgres_.+_cleanup\.py$"),
    "repositories": re.compile(r"^.+_repository\.py$"),
    "models": re.compile(r"^.+_model\.py$"),
}

VALID_ADAPTER_SUFFIXES = (
    "_provider",
    "_classifier",
    "_extractor",
    "_extraction",
    "_decoder",
    "_parser",
    "_encoder",
    "_mapping",
    "_settings",
    "_reader",
    "_assembly",
    "_tokens",
    "_credentials",
    "_lifespan",
    "_composition",
    "_codec",
    "_renderer",
    "_values",
    "_payloads",
    "_contracts",
    "_transformer",
    "_builder",
    "_probe",
    "_errors",
    "_messages",
    "_base",
    "_factory",
    "_stream",
    "_adapter",
)

CLI_NAMES = frozenset(
    {
        "authentication",
        "build_autocomplete_index",
        "configured_e2e_gate",
        "export_search_guide",
        "manage_postgres",
        "structure_pmda_xml",
        "configured_probe",
    }
)


def _to_repo_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _is_snake_case(name: str) -> bool:
    if name == "__init__.py":
        return True
    stem = name.removesuffix(".py")
    return bool(re.match(r"^[a-z][a-z0-9_]*$", stem))


def _is_reexport_only(tree: ast.AST) -> bool:
    if not isinstance(tree, ast.Module):
        return False
    has_import = False
    has_substantial_stmt = False
    for stmt in tree.body:
        # Ignore docstrings
        if (
            isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Constant)
            and isinstance(stmt.value.value, str)
        ):
            continue
        if isinstance(stmt, (ast.Import, ast.ImportFrom)):
            has_import = True
            continue
        if isinstance(stmt, ast.Assign):
            # check if it is __all__ = [...] or alias assignment foo = bar
            is_alias = False
            for target in stmt.targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id == "__all__"
                    or isinstance(target, ast.Name)
                    and isinstance(stmt.value, (ast.Name, ast.Attribute))
                ):
                    is_alias = True
            if is_alias:
                continue
        # Any other statement is substantial code (Table, MetaData, constants, classes, etc.)
        has_substantial_stmt = True
        break
    return has_import and not has_substantial_stmt


class DependencyCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.imports: list[tuple[int, str, list[str], str | None]] = []
        self.relative_imports: list[tuple[int, str]] = []
        self.wildcards: list[int] = []
        self.dynamic_calls: list[tuple[int, str]] = []
        self.defined_classes: list[
            tuple[int, str, list[str], list[str]]
        ] = []  # (line, name, bases, decorators)
        self.defined_functions: list[tuple[int, str]] = []
        self.assignments: list[tuple[int, str, str]] = []  # (line, target, value_name)
        self.sa_core_calls: list[tuple[int, str]] = []
        self.aliases: dict[str, str] = {}
        self.module_aliases: set[str] = set()

    def resolve(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return self.aliases.get(node.id, node.id)
        if isinstance(node, ast.Attribute):
            return self.resolve(node.value) + "." + node.attr
        if isinstance(node, ast.Subscript):
            return self.resolve(node.value)
        if isinstance(node, ast.Call):
            return self.resolve(node.func)
        return ""

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.module_aliases.add(alias.name)
            self.aliases[alias.asname or alias.name.split(".")[0]] = (
                alias.name if alias.asname else alias.name.split(".")[0]
            )
            self.imports.append((node.lineno, alias.name, [], alias.asname))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.level and node.level > 0:
            self.relative_imports.append(
                (node.lineno, "." * node.level + (node.module or ""))
            )
        module = node.module or ""
        symbols = [alias.name for alias in node.names]
        for alias in node.names:
            self.aliases[alias.asname or alias.name] = module + "." + alias.name
        if "*" in symbols:
            self.wildcards.append(node.lineno)
        self.imports.append((node.lineno, module, symbols, None))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # Check dynamic imports and execution
        qualified_name = self.resolve(node.func)
        func_name = qualified_name.rsplit(".", 1)[-1]

        if func_name in {"import_module", "__import__", "eval", "exec"}:
            self.dynamic_calls.append((node.lineno, func_name))

        # Core schema definitions belong only in persistence/schemas.
        if qualified_name in {"sqlalchemy.Table", "sqlalchemy.MetaData"}:
            self.sa_core_calls.append((node.lineno, func_name))

        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        bases: list[str] = []
        for b in node.bases:
            if isinstance(b, ast.Name):
                bases.append(b.id)
            elif isinstance(b, ast.Attribute):
                bases.append(b.attr)
        decorators: list[str] = []
        for d in node.decorator_list:
            if isinstance(d, ast.Name):
                decorators.append(d.id)
            elif isinstance(d, ast.Attribute):
                decorators.append(d.attr)
            elif isinstance(d, ast.Call):
                if isinstance(d.func, ast.Name):
                    decorators.append(d.func.id)
                elif isinstance(d.func, ast.Attribute):
                    decorators.append(d.func.attr)
        self.defined_classes.append((node.lineno, node.name, bases, decorators))
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.defined_functions.append((node.lineno, node.name))
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.defined_functions.append((node.lineno, node.name))
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name):
                val_name = ""
                if isinstance(node.value, ast.Name):
                    val_name = node.value.id
                elif isinstance(node.value, ast.Attribute):
                    val_name = node.value.attr
                self.assignments.append((node.lineno, target.id, val_name))
        self.generic_visit(node)


def check(
    root: Path, *, config: Path | None = None, adapter: str | None = None
) -> list[Finding]:
    root = root.resolve()

    def module_exists(name: str) -> bool:
        path = root.joinpath(*name.split("."))
        return path.with_suffix(".py").is_file() or path.is_dir()

    def collect(tree: ast.AST) -> DependencyCollector:
        result = DependencyCollector()
        result.visit(tree)
        resolved: list[tuple[int, str, list[str], str | None]] = []
        for line, module, symbols, alias in result.imports:
            remaining = []
            for symbol in symbols:
                target = module + "." + symbol
                if module_exists(target) or (
                    module == "backend"
                    and symbol
                    in {
                        "presentation",
                        "application",
                        "domain",
                        "main",
                        "infrastructure",
                        "migrations",
                    }
                ):
                    resolved.append((line, target, [], alias))
                else:
                    remaining.append(symbol)
            if remaining or not symbols:
                resolved.append((line, module, remaining, alias))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                name = result.resolve(node)
                module, _, symbol = name.rpartition(".")
                if (
                    module.startswith("backend.infrastructure.")
                    and (module_exists(module) or module in result.module_aliases)
                    and not module_exists(name)
                ):
                    resolved.append((node.lineno, module, [symbol], None))
        result.imports = resolved
        return result

    config_path = (
        config or root / "backend" / "infrastructure-architecture.toml"
    ).resolve()
    if not config_path.is_file():
        raise ValueError(f"Configuration file does not exist: {config_path}")

    with config_path.open("rb") as f:
        conf = tomllib.load(f)

    adapters_cfg: dict[str, Any] = conf.get("adapters", {})
    if not adapters_cfg:
        raise ValueError("No adapters configured in infrastructure-architecture.toml")

    # Validate configuration schema
    all_adapters = set(adapters_cfg.keys())
    for ad_name, ad_data in adapters_cfg.items():
        if not isinstance(ad_data, dict):
            raise TypeError(f"Invalid adapter config for {ad_name}")
        roles = ad_data.get("roles", [])
        if not isinstance(roles, list) or not roles or len(roles) != len(set(roles)):
            raise ValueError(f"Invalid or duplicate roles for adapter '{ad_name}'")
        for role in roles:
            valid = (
                role in PERSISTENCE_ROLE_PATTERNS
                if ad_name == "persistence"
                else role in CLI_NAMES
                if ad_name == "cli"
                else isinstance(role, str) and role.endswith(VALID_ADAPTER_SUFFIXES)
            )
            if not valid:
                raise ValueError(f"Unknown role '{role}' in adapter '{ad_name}'")
        allowed_deps = ad_data.get("allowed_dependencies", [])
        for dep in allowed_deps:
            if dep not in all_adapters:
                raise ValueError(
                    f"Unknown allowed_dependency '{dep}' in adapter '{ad_name}'"
                )

    infra_dir = root / "backend" / "infrastructure"
    if not infra_dir.is_dir():
        return []

    findings: list[Finding] = []

    def emit(p: Path | str, line: int, rule: str, msg: str) -> None:
        path_str = _to_repo_path(p if isinstance(p, Path) else Path(p), root)
        findings.append(
            Finding(path=path_str, line=max(1, line), rule=rule, message=msg)
        )

    # --- INF001: Layout, Naming, Roles ---
    # Check infrastructure root
    generated_dirs = {
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "tmp",
        "temp",
        ".tmp",
        ".venv",
        "venv",
        "node_modules",
        ".git",
        "build",
        "dist",
    }
    for child in infra_dir.iterdir():
        if child.name in generated_dirs:
            continue
        if child.is_file():
            if child.name != "__init__.py":
                emit(
                    child,
                    1,
                    "INF001",
                    f"Direct file under infrastructure root is forbidden: {child.name}",
                )
        elif child.is_dir() and child.name not in all_adapters:
            emit(child, 1, "INF001", f"Undeclared adapter directory: {child.name}")

    # Inspect all python files under infrastructure and across backend
    infra_py_files: list[Path] = [
        p
        for p in infra_dir.rglob("*.py")
        if not any(part in generated_dirs for part in p.relative_to(infra_dir).parts)
    ]

    parsed_trees: dict[Path, ast.AST] = {}
    collectors: dict[Path, DependencyCollector] = {}

    for py_file in infra_py_files:
        rel_to_infra = py_file.relative_to(infra_dir)
        ad_name = rel_to_infra.parts[0] if len(rel_to_infra.parts) > 1 else ""

        # Generic name check
        if py_file.name in GENERIC_NAMES:
            emit(
                py_file, 1, "INF001", f"Generic file name is forbidden: {py_file.name}"
            )

        # Snake_case check
        if not _is_snake_case(py_file.name):
            emit(py_file, 1, "INF001", f"File name must be snake_case: {py_file.name}")

        # Check adapter layout
        if ad_name and ad_name in adapters_cfg:
            rel_in_ad = rel_to_infra.parts[1:]
            if ad_name == "persistence":
                # Must be in one of the roles
                if len(rel_in_ad) == 1 and rel_in_ad[0] == "__init__.py":
                    pass
                elif len(rel_in_ad) == 2:
                    role_dir = rel_in_ad[0]
                    file_name = rel_in_ad[1]
                    if role_dir not in PERSISTENCE_ROLE_PATTERNS:
                        emit(
                            py_file,
                            1,
                            "INF001",
                            f"Undeclared persistence role directory: {role_dir}",
                        )
                    else:
                        pattern = PERSISTENCE_ROLE_PATTERNS[role_dir]
                        if file_name != "__init__.py" and not pattern.match(file_name):
                            emit(
                                py_file,
                                1,
                                "INF001",
                                f"File {file_name} in persistence/{role_dir} does not match expected role pattern",
                            )
                else:
                    emit(
                        py_file,
                        1,
                        "INF001",
                        f"Deep or misplaced file in persistence: {rel_to_infra.as_posix()}",
                    )
            else:
                # Non-persistence adapters are flat; roles declare existing names,
                # while suffix vocabulary also permits new subjects.
                if len(rel_in_ad) != 1:
                    emit(
                        py_file,
                        1,
                        "INF001",
                        f"Deep arbitrary directory in {ad_name}: {rel_to_infra.as_posix()}",
                    )
                elif py_file.name != "__init__.py":
                    valid_name = (
                        py_file.stem in CLI_NAMES
                        if ad_name == "cli"
                        else py_file.stem.endswith(VALID_ADAPTER_SUFFIXES)
                    )
                    if not valid_name:
                        emit(
                            py_file,
                            1,
                            "INF001",
                            "File must use a declared role suffix or CLI command name",
                        )

        # Parse AST (INF000)
        try:
            content = py_file.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(py_file))
            parsed_trees[py_file] = tree
            col = collect(tree)
            collectors[py_file] = col
        except SyntaxError as e:
            emit(py_file, e.lineno or 1, "INF000", f"Syntax error: {e.msg}")
            continue

        # Check __init__.py rules and re-exports (INF004)
        if py_file.name == "__init__.py":
            # Must be empty or docstring only
            body = tree.body
            for stmt in body:
                if (
                    isinstance(stmt, ast.Expr)
                    and isinstance(stmt.value, ast.Constant)
                    and isinstance(stmt.value.value, str)
                ):
                    continue  # Docstring
                emit(
                    py_file,
                    stmt.lineno,
                    "INF004",
                    "__init__.py must be empty or docstring only",
                )
                break
        else:
            # Check re-export-only module (no substantial code, only imports and alias re-exports)
            if _is_reexport_only(tree):
                emit(
                    py_file,
                    1,
                    "INF004",
                    "Re-export only module is forbidden",
                )

        # Check relative imports (INF002)
        col = collectors[py_file]
        for lineno, rel_mod in col.relative_imports:
            emit(py_file, lineno, "INF002", f"Relative import is forbidden: {rel_mod}")

        # Check wildcard imports (INF003)
        for lineno in col.wildcards:
            emit(py_file, lineno, "INF003", "Wildcard import is forbidden")

        # Check dynamic import / bypasses (INF009)
        for lineno, func_name in col.dynamic_calls:
            emit(
                py_file,
                lineno,
                "INF009",
                f"Dynamic execution or import bypass is forbidden: {func_name}",
            )

        # Check Core Table misplaced definition (INF010)
        if "persistence" in py_file.parts:
            role = py_file.parent.name
            if role != "schemas":
                for lineno, _ in col.sa_core_calls:
                    emit(
                        py_file,
                        lineno,
                        "INF010",
                        f"Core Table/MetaData definition is forbidden in {role}, only allowed in schemas",
                    )
            classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
            if role == "repositories" and py_file.name != "__init__.py":

                def domain_protocol(
                    base: ast.AST, collector: DependencyCollector = col
                ) -> bool:
                    name = collector.resolve(base)
                    module, _, symbol = name.rpartition(".")
                    if not module.startswith("backend.domain.") or not module.endswith(
                        ".repositories"
                    ):
                        return False
                    path = root.joinpath(*module.split(".")).with_suffix(".py")
                    if not path.is_file():
                        return False
                    protocol_tree = ast.parse(path.read_text(encoding="utf-8"))
                    protocol_col = collect(protocol_tree)
                    return any(
                        isinstance(n, ast.ClassDef)
                        and n.name == symbol
                        and any(
                            protocol_col.resolve(b)
                            in {"typing.Protocol", "typing_extensions.Protocol"}
                            for b in n.bases
                        )
                        for n in ast.walk(protocol_tree)
                    )

                has_repo_base = bool(classes) and all(
                    any(domain_protocol(base) for base in cls.bases) for cls in classes
                )
                if not has_repo_base:
                    emit(
                        py_file,
                        1,
                        "INF010",
                        "Repository must explicitly implement a Domain repository protocol",
                    )
            orm_bases = {
                "sqlalchemy.orm.DeclarativeBase",
                "sqlalchemy.orm.DeclarativeBaseNoMeta",
            }
            local_bases: set[str] = {
                target.id
                for node in ast.walk(tree)
                if isinstance(node, ast.Assign)
                and isinstance(node.value, ast.Call)
                and col.resolve(node.value.func) == "sqlalchemy.orm.declarative_base"
                for target in node.targets
                if isinstance(target, ast.Name)
            }
            for cls in classes:
                if any(
                    col.resolve(b) in orm_bases or col.resolve(b) in local_bases
                    for b in cls.bases
                ):
                    local_bases.add(cls.name)
            registries = {
                n.targets[0].id
                for n in ast.walk(tree)
                if isinstance(n, ast.Assign)
                and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name)
                and isinstance(n.value, ast.Call)
                and col.resolve(n.value.func) == "sqlalchemy.orm.registry"
            }
            mapped_classes = set()
            for cls in classes:
                mapped = any(
                    col.resolve(d).removesuffix(".mapped") in registries
                    and col.resolve(d).endswith(".mapped")
                    for d in cls.decorator_list
                )
                table_name = any(
                    isinstance(n, (ast.Assign, ast.AnnAssign))
                    and any(
                        isinstance(t, ast.Name) and t.id == "__tablename__"
                        for t in (
                            n.targets if isinstance(n, ast.Assign) else [n.target]
                        )
                    )
                    for n in cls.body
                )
                if mapped or (cls.name in local_bases and table_name):
                    mapped_classes.add(cls.name)
            if role == "schemas" and (mapped_classes or local_bases):
                emit(py_file, 1, "INF010", "ORM classes are forbidden in Core schemas")
            if role == "models" and py_file.name != "__init__.py":
                common_bases = {
                    c.name
                    for c in classes
                    if any(col.resolve(b) in orm_bases for b in c.bases)
                }
                if not mapped_classes or any(
                    c.name not in mapped_classes | common_bases for c in classes
                ):
                    emit(
                        py_file,
                        1,
                        "INF010",
                        "Classes in models/ must be ORM mapped classes (DeclarativeBase/Mapped)",
                    )

    # --- INF005: Onion / Outer-layer reverse dependency & Inter-layer imports ---
    # Scan domain, application, presentation to detect direct imports into infrastructure
    for layer in ["domain", "application", "presentation"]:
        layer_dir = root / "backend" / layer
        if not layer_dir.is_dir():
            continue
        for py_path in layer_dir.rglob("*.py"):
            if any(
                part in generated_dirs for part in py_path.relative_to(layer_dir).parts
            ):
                continue
            try:
                content = py_path.read_text(encoding="utf-8")
                tree = ast.parse(content, filename=str(py_path))
            except (OSError, SyntaxError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("backend.infrastructure"):
                            emit(
                                py_path,
                                node.lineno,
                                "INF005",
                                f"{layer.capitalize()} layer must not import infrastructure: {alias.name}",
                            )
                elif isinstance(node, ast.ImportFrom) and (
                    node.module or ""
                ).startswith("backend.infrastructure"):
                    emit(
                        py_path,
                        node.lineno,
                        "INF005",
                        f"{layer.capitalize()} layer must not import infrastructure: {node.module}",
                    )

    # Check infrastructure files importing presentation, main, migrations
    for py_file, col in collectors.items():
        rel_to_infra = py_file.relative_to(infra_dir)
        is_probe = rel_to_infra.as_posix() in {
            "cli/configured_probe.py",
            "composition/configured_probe.py",
        }
        for lineno, mod, _, _ in col.imports:
            if mod.startswith("backend.presentation"):
                emit(
                    py_file,
                    lineno,
                    "INF005",
                    f"Infrastructure must not depend on presentation: {mod}",
                )
            elif mod.startswith("backend.main"):
                if not is_probe:
                    emit(
                        py_file,
                        lineno,
                        "INF005",
                        f"Infrastructure must not depend on backend.main: {mod}",
                    )
            elif mod.startswith("backend.migrations"):
                emit(
                    py_file,
                    lineno,
                    "INF005",
                    f"Infrastructure must not depend on backend.migrations: {mod}",
                )

    # --- INF006: Inter-adapter and persistence role dependency directions ---
    for py_file, col in collectors.items():
        rel_to_infra = py_file.relative_to(infra_dir)
        current_adapter = rel_to_infra.parts[0] if len(rel_to_infra.parts) > 1 else ""
        allowed_deps = set(
            adapters_cfg.get(current_adapter, {}).get("allowed_dependencies", [])
        )
        allowed_deps.add(current_adapter)

        for lineno, mod, symbols, _ in col.imports:
            if (
                current_adapter == "persistence"
                and len(rel_to_infra.parts) > 2
                and rel_to_infra.parts[1] == "records"
                and mod.startswith("backend.application.")
            ):
                emit(
                    py_file,
                    lineno,
                    "INF006",
                    "Records must not depend on Application DTOs or command results",
                )
            if not mod.startswith("backend.infrastructure."):
                continue
            target_parts = mod.removeprefix("backend.infrastructure.").split(".")
            target_adapter = target_parts[0]

            # Inter-adapter check
            if (
                current_adapter
                and target_adapter != current_adapter
                and target_adapter not in allowed_deps
            ):
                emit(
                    py_file,
                    lineno,
                    "INF006",
                    f"Adapter '{current_adapter}' is forbidden to depend on adapter '{target_adapter}' ({mod})",
                )

            # Persistence internal role dependency check
            if (
                current_adapter == "persistence"
                and target_adapter == "persistence"
                and len(rel_to_infra.parts) > 2
                and len(target_parts) > 1
            ):
                src_role = rel_to_infra.parts[1]
                target_role = target_parts[1]

                # schemas and runtime base cannot depend on higher roles
                if src_role in {"schemas", "runtime"} and target_role in {
                    "queries",
                    "stores",
                    "registration",
                    "maintenance",
                }:
                    emit(
                        py_file,
                        lineno,
                        "INF006",
                        f"Persistence role '{src_role}' must not depend on '{target_role}' ({mod})",
                    )
                # mappings cannot depend on schemas, queries, stores, publisher
                if src_role == "mappings" and target_role in {
                    "schemas",
                    "queries",
                    "stores",
                    "registration",
                }:
                    emit(
                        py_file,
                        lineno,
                        "INF006",
                        f"Persistence role 'mappings' must not depend on '{target_role}' ({mod})",
                    )
                # maintenance cannot depend on registration
                if src_role == "maintenance" and target_role == "registration":
                    emit(
                        py_file,
                        lineno,
                        "INF006",
                        f"Persistence role 'maintenance' must not depend on 'registration' ({mod})",
                    )
                # queries/stores/registration cannot depend on each other's adapters
                if (
                    src_role in {"queries", "stores", "registration"}
                    and target_role in {"queries", "stores", "registration"}
                    and src_role != target_role
                ):
                    emit(
                        py_file,
                        lineno,
                        "INF006",
                        f"Persistence role '{src_role}' must not depend on '{target_role}' ({mod})",
                    )

            # Serialization renderer -> codec check
            if current_adapter == "serialization" and target_adapter == "serialization":
                src_stem = py_file.stem
                if (
                    "renderer" in src_stem
                    and len(target_parts) > 1
                    and "codec" in target_parts[1]
                ):
                    emit(
                        py_file,
                        lineno,
                        "INF006",
                        f"Renderer must not depend on codec ({mod})",
                    )

    # --- INF007: Public scope, symbols, and consumers ---
    # Check all imports into infrastructure from anywhere in root
    all_source_files: list[Path] = [
        p
        for p in root.rglob("*.py")
        if not any(
            part in generated_dirs or part.startswith(".")
            for part in p.relative_to(root).parts
        )
    ]

    for py_file in all_source_files:
        repo_rel_path = _to_repo_path(py_file, root)
        # Skip test files from consumer enforcement
        is_test = (
            repo_rel_path.startswith("backend/tests/") or "tests/" in repo_rel_path
        )

        # Determine caller consumer identity
        consumer_category = ""
        if repo_rel_path.startswith("backend/infrastructure/composition/"):
            consumer_category = "composition"
        elif repo_rel_path.startswith("backend/infrastructure/cli/"):
            consumer_category = "cli"
        elif repo_rel_path == "backend/main.py":
            consumer_category = "backend.main"
        elif repo_rel_path == "backend/migrations/postgres/env.py":
            consumer_category = "backend/migrations/postgres/env.py"
        elif repo_rel_path.startswith("backend/migrations/"):
            consumer_category = "backend/migrations"
        elif repo_rel_path.startswith("frontend/scripts/"):
            consumer_category = "frontend/scripts"
        elif repo_rel_path.startswith("backend/infrastructure/persistence/"):
            consumer_category = "persistence"
        elif repo_rel_path.startswith("backend/infrastructure/pmda_xml/"):
            consumer_category = "pmda_xml"
        elif repo_rel_path.startswith("backend/infrastructure/"):
            consumer_category = repo_rel_path.removeprefix(
                "backend/infrastructure/"
            ).split("/")[0]

        # Parse if not already in collectors
        file_col = collectors.get(py_file)
        if file_col is None:
            try:
                tree = ast.parse(
                    py_file.read_text(encoding="utf-8"), filename=str(py_file)
                )
                file_col = collect(tree)
            except (OSError, SyntaxError):
                continue

        for lineno, mod, symbols, asname in file_col.imports:
            if not mod.startswith("backend.infrastructure."):
                continue
            parts = mod.removeprefix("backend.infrastructure.").split(".")
            target_ad = parts[0]
            rel_module = "/".join(parts[1:])

            # If caller is within the same adapter package, public module boundary doesn't apply
            if consumer_category == target_ad and not (
                target_ad == "persistence"
                and repo_rel_path.startswith("backend/infrastructure/persistence/")
            ):
                continue

            # Within persistence, check cross-role access if applicable
            if consumer_category == "persistence" and target_ad == "persistence":
                # Allowed internal roles
                continue

            if is_test:
                continue

            public_entries = adapters_cfg.get(target_ad, {}).get("public", {})
            # Look up matching public module
            entry = None
            for pub_mod, pub_info in public_entries.items():
                if rel_module == pub_mod or rel_module.startswith(pub_mod + "/"):
                    entry = pub_info
                    break

            if not entry:
                emit(
                    py_file,
                    lineno,
                    "INF007",
                    f"Module '{mod}' is not declared as public in adapter '{target_ad}'",
                )
                continue

            # Check allowed consumers
            allowed_consumers = set(entry.get("consumers", []))
            # Match consumer
            consumer_matched = False
            for ac in allowed_consumers:
                if ac == consumer_category:
                    consumer_matched = True
                    break
                if (
                    ac == "cli/manage_postgres"
                    and repo_rel_path == "backend/infrastructure/cli/manage_postgres.py"
                ):
                    consumer_matched = True
                    break
                if ac == "persistence" and consumer_category == "persistence":
                    consumer_matched = True
                    break
                if ac in {"migrations", "backend/migrations"} and (
                    consumer_category == "backend/migrations"
                    or consumer_category == "backend/migrations/postgres/env.py"
                    or repo_rel_path.startswith("backend/migrations/")
                ):
                    consumer_matched = True
                    break
                if (
                    ac == "backend/migrations/postgres/env.py"
                    and consumer_category == "backend/migrations/postgres/env.py"
                ):
                    consumer_matched = True
                    break
                if ac == "persistence.registration" and repo_rel_path.startswith(
                    "backend/infrastructure/persistence/registration/"
                ):
                    consumer_matched = True
                    break
                if (
                    ac == "persistence.runtime.postgres_readiness"
                    and repo_rel_path.startswith(
                        "backend/infrastructure/persistence/runtime/postgres_readiness"
                    )
                ):
                    consumer_matched = True
                    break

            if not consumer_matched:
                emit(
                    py_file,
                    lineno,
                    "INF007",
                    f"Consumer '{repo_rel_path}' is not permitted to use public module '{mod}' (allowed: {sorted(allowed_consumers)})",
                )

            # Check symbols if imported via from ... import sym
            declared_symbols = set(entry.get("symbols", []))
            for sym in symbols:
                if sym.startswith("_") or sym not in declared_symbols:
                    emit(
                        py_file,
                        lineno,
                        "INF007",
                        f"Symbol '{sym}' is not a declared public export of '{mod}'",
                    )

    # --- INF008: Dependency Cycles ---
    # Build graph of infrastructure modules
    adj: dict[str, set[str]] = defaultdict(set)
    mod_locations: dict[tuple[str, str], tuple[Path, int]] = {}

    for py_file, col in collectors.items():
        src_mod = "backend.infrastructure." + py_file.relative_to(
            infra_dir
        ).with_suffix("").as_posix().replace("/", ".")
        for lineno, target_mod, _, _ in col.imports:
            if target_mod.startswith("backend.infrastructure."):
                adj[src_mod].add(target_mod)
                mod_locations[(src_mod, target_mod)] = (py_file, lineno)

    # Detect cycles with DFS
    visited: set[str] = set()
    stack: list[str] = []
    cycle_reported: set[frozenset[str]] = set()

    def dfs(node: str) -> None:
        if node in stack:
            cycle = stack[stack.index(node) :]
            cycle_key = frozenset(cycle)
            if cycle_key not in cycle_reported:
                cycle_reported.add(cycle_key)
                # Emit finding at the back-edge location
                prev = cycle[-1]
                loc = mod_locations.get((prev, node))
                if loc:
                    emit(
                        loc[0],
                        loc[1],
                        "INF008",
                        f"Dependency cycle detected: {' -> '.join(cycle)} -> {node}",
                    )
            return
        if node in visited:
            return

        visited.add(node)
        stack.append(node)
        for neighbor in adj.get(node, []):
            dfs(neighbor)
        stack.pop()

    for m in list(adj.keys()):
        dfs(m)

    # Filter by adapter if requested
    if adapter:
        findings = [
            f
            for f in findings
            if f.path.startswith(f"backend/infrastructure/{adapter}/")
        ]

    return sorted(set(findings), key=lambda f: (f.path, f.line, f.rule, f.message))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[2]
    )
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--adapter", type=str, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    if not root.is_dir():
        print(f"Error: root directory does not exist: {root}", file=sys.stderr)
        return 2

    config_path = (
        args.config or root / "backend" / "infrastructure-architecture.toml"
    ).resolve()
    if not config_path.is_file():
        print(
            f"Error: configuration file does not exist: {config_path}", file=sys.stderr
        )
        return 2

    try:
        findings = check(root, config=config_path, adapter=args.adapter)
    except (OSError, ValueError, KeyError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps([asdict(f) for f in findings], ensure_ascii=False, indent=2))
    else:
        for f in findings:
            print(f"{f.path}:{f.line}: {f.rule} {f.message}")
        print(
            f"{len(findings)} findings; {dict(sorted(Counter(f.rule for f in findings).items()))}"
        )

    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
