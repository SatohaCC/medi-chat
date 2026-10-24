"""Static Application boundary checker. Never imports inspected application code."""

from __future__ import annotations

import argparse
import ast
import json
import sys
import tomllib
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, order=True)
class Finding:
    path: str
    line: int
    rule: str
    message: str
    feature: str = ""


IMPORT_RULES = frozenset(
    {"APP002", "APP003", "APP004", "APP005", "APP009", "APP010", "APP011", "APP000"}
)
ROOT_ROLES = {"values": "values", "policies": "policies", "errors": "errors"}
ROLE_DEPENDENCIES = {
    "commands": {
        "command_services",
        "command_interfaces",
        "command_models",
        "command_dtos",
        "command_policies",
        "interfaces",
        "values",
        "policies",
        "errors",
    },
    "queries": {
        "query_services",
        "query_readers",
        "query_interfaces",
        "query_models",
        "query_dtos",
        "query_policies",
        "interfaces",
        "values",
        "policies",
        "errors",
    },
    "command_services": {
        "command_services",
        "command_interfaces",
        "command_models",
        "command_dtos",
        "command_policies",
        "interfaces",
        "values",
        "policies",
        "errors",
    },
    "query_services": {
        "query_services",
        "query_readers",
        "query_interfaces",
        "query_models",
        "query_dtos",
        "query_policies",
        "interfaces",
        "values",
        "policies",
        "errors",
    },
    "command_interfaces": {
        "command_interfaces",
        "command_models",
        "command_dtos",
        "values",
        "errors",
    },
    "query_readers": {
        "query_readers",
        "query_models",
        "query_dtos",
        "values",
        "errors",
    },
    "query_interfaces": {
        "query_interfaces",
        "query_readers",
        "query_models",
        "query_dtos",
        "values",
        "errors",
    },
    "command_models": {"values", "errors"},
    "query_models": {"values", "errors"},
    "command_dtos": {"command_models", "command_dtos", "values", "errors"},
    "query_dtos": {"query_models", "query_dtos", "values", "errors"},
    "command_policies": {
        "command_models",
        "command_dtos",
        "command_policies",
        "values",
        "policies",
        "errors",
    },
    "query_policies": {
        "query_models",
        "query_dtos",
        "query_policies",
        "values",
        "policies",
        "errors",
    },
    "interfaces": {
        "interfaces",
        "command_models",
        "command_dtos",
        "query_models",
        "query_dtos",
        "values",
        "errors",
    },
    "values": {"errors"},
    "policies": {"values", "errors", "policies"},
    "errors": set(),
}


def module_side(parts: list[str]) -> str | None:
    if not parts:
        return None
    if parts[0] in {"commands", "queries"}:
        return parts[0]
    if (
        parts[0] == "interfaces"
        and len(parts) >= 2
        and parts[1].endswith(("_query_reader", "_reader"))
    ):
        return "queries"
    return None


TECHNICAL_MODULES = {
    "threading",
    "concurrent",
    "multiprocessing",
    "subprocess",
    "sqlite3",
    "socket",
    "http",
    "urllib",
    "importlib",
}


def module_role(parts: list[str]) -> str | None:
    if not parts:
        return None
    if parts[0] == "common":
        return None
    generic = {"command", "query", "handler", "result", "dto", "service"}
    if len(parts) == 1:
        return ROOT_ROLES.get(parts[0])
    if len(parts) == 2 and parts[0] in {"interfaces", "policies"}:
        return parts[0] if parts[1] not in generic else None
    side = module_side(parts)
    if side:
        prefix = "command" if side == "commands" else "query"
        if len(parts) == 2:
            if parts[1] == "models":
                return f"{prefix}_models"
            return (
                side
                if parts[1]
                not in generic
                | {"services", "interfaces", "readers", "dtos", "policies"}
                else None
            )
        if len(parts) == 3 and parts[1] in {
            "services",
            "interfaces",
            "dtos",
            "policies",
        } | ({"readers"} if side == "queries" else set()):
            return f"{prefix}_{parts[1]}" if parts[2] not in generic else None
    return None


def check(
    root: Path, config: dict, *, phase: str = "all", feature: str | None = None
) -> list[Finding]:
    application = root / "backend" / "application"
    if not application.is_dir():
        raise ValueError(f"Application directory not found: {application}")
    features = config["features"]
    # A dependency declaration must describe a DAG, not legalize a cycle.
    visited: set[str] = set()
    active: set[str] = set()

    def visit(name: str) -> None:
        if name in active:
            raise ValueError(f"Feature dependency cycle: {name}")
        if name in visited:
            return
        if name not in features:
            raise ValueError(f"Unknown dependency feature: {name}")
        active.add(name)
        for dependency in features[name].get("depends_on", []):
            visit(dependency)
        active.remove(name)
        visited.add(name)

    for name in features:
        visit(name)
    findings: set[Finding] = set()
    node: ast.AST
    edges: dict[str, set[str]] = {}
    edge_locations: dict[tuple[str, str], tuple[Path, int]] = {}

    def emit(
        path: Path, line: int, rule: str, message: str, *, scope: str = ""
    ) -> None:
        relative = path.relative_to(root)
        owner = (
            relative.parts[2]
            if len(relative.parts) > 3 and relative.parts[1] == "application"
            else scope
        )
        findings.add(Finding(relative.as_posix(), line, rule, message, owner))

    for path in sorted(application.rglob("*.py")):
        rel = path.relative_to(application)
        if "__pycache__" in rel.parts:
            continue
        if feature is not None and (len(rel.parts) < 2 or rel.parts[0] != feature):
            continue
        module = ".".join(path.relative_to(root).with_suffix("").parts)
        source_feature = rel.parts[0] if len(rel.parts) >= 2 else None
        parts = list(rel.with_suffix("").parts[1:])
        source_role = module_role(parts)
        if source_feature == "common" and len(parts) == 2 and parts[0] == "dtos":
            source_role = "query_dtos"
        if source_feature is None and rel.name != "__init__.py":
            emit(path, 1, "APP001", "Place code inside a declared feature")
        if source_feature not in {None, "common"} and source_feature not in features:
            emit(path, 1, "APP001", f"Undeclared feature: {source_feature}")
        if (
            source_feature == "common"
            and rel.name != "__init__.py"
            and source_role not in {"values", "errors", "query_dtos"}
        ):
            emit(
                path,
                1,
                "APP001",
                "common contains only feature-neutral data/value/error modules",
            )
        if (
            rel.name != "__init__.py"
            and source_feature != "common"
            and source_role is None
        ):
            emit(
                path,
                1,
                "APP001",
                "Use commands/queries slices with side-local services/readers/DTOs; no feature-root services/ports/models/DTOs",
            )
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        except SyntaxError as exc:
            emit(path, exc.lineno or 1, "APP000", f"Syntax error: {exc.msg}")
            continue
        if rel.name == "__init__.py":
            # Package markers contain only an optional docstring; no re-export loophole.
            for node in tree.body:
                if not (
                    isinstance(node, ast.Expr)
                    and isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, str)
                ):
                    emit(
                        path,
                        node.lineno,
                        "APP004",
                        "Keep __init__.py empty except for a docstring",
                    )
        for node in ast.walk(tree):
            targets: list[str] = []
            if isinstance(node, ast.Import):
                targets = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    emit(
                        path,
                        node.lineno,
                        "APP002",
                        "Use absolute imports beginning with backend",
                    )
                    package = module.split(".")[:-1]
                    base_parts = package[: len(package) - node.level + 1]
                    base = ".".join(base_parts + ([node.module] if node.module else []))
                else:
                    base = node.module or ""
                if any(alias.name == "*" for alias in node.names):
                    emit(path, node.lineno, "APP003", "Wildcard imports are forbidden")
                targets = [base]
                # Resolve package-form imports too: from backend.application.x import models.
                for alias in node.names:
                    candidate = f"{base}.{alias.name}"
                    candidate_path = root.joinpath(*candidate.split("."))
                    if (
                        candidate_path.with_suffix(".py").is_file()
                        or candidate_path.is_dir()
                    ):
                        targets.append(candidate)
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "__import__"
            ):
                emit(
                    path,
                    node.lineno,
                    "APP011",
                    "Dynamic imports bypass static boundaries",
                )
            if not isinstance(node, (ast.Import, ast.ImportFrom, ast.Call)):
                continue
            for target in targets:
                source_side = module_side(parts)
                if (
                    source_side != "commands"
                    and target.startswith("backend.domain.")
                    and "repositories" in target.split(".")
                ):
                    emit(
                        path,
                        node.lineno,
                        "APP015",
                        "Queries must use QueryReaders, not Domain repositories",
                    )
                top = target.split(".")[0]
                if top in TECHNICAL_MODULES:
                    emit(
                        path,
                        node.lineno,
                        "APP010",
                        f"Technical IO/execution belongs outside Application: {target}",
                    )
                if top not in sys.stdlib_module_names and top != "backend":
                    emit(
                        path,
                        node.lineno,
                        "APP005",
                        f"Only standard library, Application and Domain may be imported: {target}",
                    )
                # Parent package imports are resolved through candidate targets above.
                if (
                    top == "backend"
                    and not target.startswith(
                        ("backend.application.", "backend.domain.")
                    )
                    and target not in {"backend.application", "backend.domain"}
                ):
                    emit(
                        path,
                        node.lineno,
                        "APP005",
                        f"Forbidden outer-layer dependency: {target}",
                    )
                if source_feature == "common" and target.startswith("backend.domain."):
                    emit(
                        path,
                        node.lineno,
                        "APP009",
                        "common must not depend on domain features",
                    )
                if not target.startswith("backend.application."):
                    continue
                target_parts = target.split(".")
                target_feature = target_parts[2]
                target_tail = target_parts[3:]
                if (
                    (not target_tail or root.joinpath(*target.split(".")).is_dir())
                    and isinstance(node, ast.ImportFrom)
                    and len(targets) > 1
                ):
                    continue
                target_role = module_role(target_tail)
                target_side = module_side(target_tail)
                if target_feature == "common" and target_tail[:1] == ["dtos"]:
                    target_side = "queries"
                if source_side and target_side and source_side != target_side:
                    emit(
                        path,
                        node.lineno,
                        "APP014",
                        "Command and Query handlers, readers and DTOs must not be shared",
                    )

                if (
                    source_feature == target_feature
                    and target != module
                    and source_role
                    and target_role
                ):
                    edges.setdefault(module, set()).add(target)
                    edge_locations[(module, target)] = (path, node.lineno)
                if (
                    source_feature != target_feature
                    and source_role in {"commands", "queries"}
                    and target_role in {"commands", "queries"}
                ):
                    emit(
                        path,
                        node.lineno,
                        "APP007",
                        "Use-case slices must not directly compose other use-case slices",
                    )
                if source_feature == "common" and target_feature != "common":
                    emit(
                        path,
                        node.lineno,
                        "APP009",
                        "common must not depend on features",
                    )
                elif target_feature != source_feature and target_feature != "common":
                    allowed = features.get(source_feature, {}).get("depends_on", [])
                    if target_feature not in allowed:
                        emit(
                            path,
                            node.lineno,
                            "APP008",
                            f"Undeclared feature dependency: {source_feature} -> {target_feature}",
                        )
                    public = features.get(target_feature, {}).get("public_modules", [])
                    if ".".join(target_tail) not in public:
                        emit(
                            path,
                            node.lineno,
                            "APP008",
                            f"Not a declared public module: {target}",
                        )
                elif source_feature == target_feature and target != module:
                    if (
                        target_role in {"commands", "queries"}
                        and source_role is not None
                    ):
                        emit(
                            path,
                            node.lineno,
                            "APP007",
                            "Handlers and side-local services must not import other handlers",
                        )
                    elif (
                        source_role
                        and target_role
                        and target_role not in ROLE_DEPENDENCIES[source_role]
                    ):
                        emit(
                            path,
                            node.lineno,
                            "APP006",
                            f"Forbidden role dependency: {source_role} -> {target_role}",
                        )
    # Same-role composition is legal only when module dependencies remain acyclic.
    done: set[str] = set()
    walking: set[str] = set()

    def visit_module(module: str) -> None:
        if module in done:
            return
        walking.add(module)
        for target in sorted(edges.get(module, set())):
            if target in walking:
                path, line = edge_locations[(module, target)]
                emit(
                    path,
                    line,
                    "APP012",
                    f"Application module dependency cycle: {module} -> {target}",
                )
            else:
                visit_module(target)
        walking.remove(module)
        done.add(module)

    for module in sorted(edges):
        visit_module(module)

    # Consumers outside Application must also respect its public surface.
    for path in sorted((root / "backend").rglob("*.py")):
        relative = path.relative_to(root / "backend")
        if relative.parts[0] in {"application", "tests", ".venv", "migrations"}:
            continue
        if "__pycache__" in relative.parts:
            continue
        module = ".".join(path.relative_to(root).with_suffix("").parts)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        except SyntaxError:
            continue  # The language checker owns syntax outside Application.
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.Import):
                targets = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                package = module.split(".")[:-1]
                base = (
                    ".".join(
                        package[: len(package) - node.level + 1]
                        + ([node.module] if node.module else [])
                    )
                    if node.level
                    else node.module or ""
                )
                targets = [base]
                for alias in node.names:
                    candidate = f"{base}.{alias.name}"
                    candidate_path = root.joinpath(*candidate.split("."))
                    if (
                        candidate_path.with_suffix(".py").is_file()
                        or candidate_path.is_dir()
                    ):
                        targets.append(candidate)
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            for target in targets:
                if not target.startswith("backend.application."):
                    continue
                parts = target.split(".")
                target_feature = parts[2]
                if feature is not None and target_feature != feature:
                    continue
                tail = parts[3:]
                if not tail and isinstance(node, ast.ImportFrom) and len(targets) > 1:
                    continue  # Inspect the resolved child rather than its package.
                public = features.get(target_feature, {}).get("public_modules", [])
                if ".".join(tail) not in public:
                    emit(
                        path,
                        node.lineno,
                        "APP008",
                        f"Not a declared public Application module: {target}",
                        scope=target_feature,
                    )
                if relative.parts[0] == "presentation" and module_role(tail) in {
                    "interfaces",
                    "policies",
                    "values",
                    "command_interfaces",
                    "query_interfaces",
                    "query_readers",
                    "command_services",
                    "query_services",
                    "command_policies",
                    "query_policies",
                }:
                    emit(
                        path,
                        node.lineno,
                        "APP013",
                        "Presentation uses public use cases and DTOs, not internal ports/policies/values",
                        scope=target_feature,
                    )
    if phase == "imports":
        return sorted(f for f in findings if f.rule in IMPORT_RULES)
    if phase == "enforced":
        enforced = set(config.get("enforced_features", []))
        unknown = enforced - set(features)
        if unknown:
            raise ValueError(f"Unknown enforced features: {sorted(unknown)}")
        return sorted(
            f for f in findings if f.rule in IMPORT_RULES or f.feature in enforced
        )
    return sorted(findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[2]
    )
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument(
        "--phase", choices=("imports", "enforced", "all"), default="all"
    )
    parser.add_argument("--feature")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        with (args.config or root / "backend" / "application-architecture.toml").open(
            "rb"
        ) as stream:
            config = tomllib.load(stream)
        if (
            args.feature
            and args.feature not in config["features"]
            and args.feature != "common"
        ):
            raise ValueError(f"Unknown feature: {args.feature}")
        findings = check(root, config, phase=args.phase, feature=args.feature)
    except (OSError, ValueError, KeyError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps([asdict(f) for f in findings], ensure_ascii=False, indent=2))
    else:
        for finding in findings:
            print(f"{finding.path}:{finding.line}: {finding.rule} {finding.message}")
        print(
            f"{len(findings)} findings; {dict(sorted(Counter(f.rule for f in findings).items()))}"
        )
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
