"""Static Layer & Presentation Architecture checker.

Validates:
- Four-layer Onion architecture rules and root directory layout (LAY001, LAY002)
- Technology independence of inner layers (Domain & Application) (LAY003)
- No legacy facade or package imports (LAY004)
- Infrastructure root layout (LAY005)
- Presentation response DTO boundaries (LAY006)
"""

from __future__ import annotations

import argparse
import ast
import json
from collections import Counter
from contextlib import suppress
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, order=True)
class Finding:
    path: str
    line: int
    rule: str
    message: str


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

ALLOWED_INFRASTRUCTURE_PACKAGES = {
    "observability",
    "authentication",
    "cli",
    "composition",
    "intent",
    "llm",
    "morphology",
    "package_insert_definitions",
    "persistence",
    "pmda_xml",
    "serialization",
    "document_import",
    "sources",
}

OUTPUT_RESPONSE_DTOS = {
    "backend.presentation.chat_models.ChatResponse",
    "backend.presentation.evidence_models.ChatSource",
    "backend.presentation.medicine_models.MedicineMatch",
}


def _extract_aliases(tree: ast.AST, module_name: str) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for imported in node.names:
                aliases[imported.asname or imported.name.split(".")[0]] = (
                    imported.name if imported.asname else imported.name.split(".")[0]
                )
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                package = module_name.split(".")[: -node.level]
                base = ".".join(package + ([base] if base else []))
            for imported in node.names:
                dependency = f"{base}.{imported.name}" if base else imported.name
                aliases[imported.asname or imported.name] = dependency
    return aliases


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
        return set()
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


def _qualified_name(node: ast.AST, aliases: dict[str, str]) -> str:
    parts = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        base = aliases.get(current.id, current.id)
        return ".".join([base] + list(reversed(parts)))
    return ".".join(reversed(parts))


def check(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    backend_root = root / "backend"
    if not backend_root.is_dir():
        return findings

    # LAY001: Backend root onion directories
    for child in backend_root.iterdir():
        if (
            child.is_dir()
            and not child.name.startswith((".", "__"))
            and child.name not in ALLOWED_BACKEND_DIRECTORIES
        ):
            findings.append(
                Finding(
                    path=str(child.relative_to(root)).replace("\\", "/"),
                    line=1,
                    rule="LAY001",
                    message=f"Disallowed root backend directory: '{child.name}'. Allowed: {sorted(ALLOWED_BACKEND_DIRECTORIES)}",
                )
            )

    # LAY002: Tracked production packages must define __init__.py
    for layer in ("domain", "application", "infrastructure", "presentation", "config"):
        layer_path = backend_root / layer
        if not layer_path.is_dir():
            continue
        for directory in layer_path.rglob("*"):
            if directory.is_dir() and not directory.name.startswith((".", "__")):
                py_files = [p for p in directory.glob("*.py") if p.is_file()]
                if py_files and not (directory / "__init__.py").exists():
                    findings.append(
                        Finding(
                            path=str(directory.relative_to(root)).replace("\\", "/"),
                            line=1,
                            rule="LAY002",
                            message=f"Package '{directory.name}' contains python files but lacks '__init__.py'",
                        )
                    )

    # LAY005: Infrastructure root layout
    infra_root = backend_root / "infrastructure"
    if infra_root.is_dir():
        for child in infra_root.iterdir():
            if (
                child.is_dir()
                and not child.name.startswith((".", "__"))
                and child.name not in ALLOWED_INFRASTRUCTURE_PACKAGES
            ):
                findings.append(
                    Finding(
                        path=str(child.relative_to(root)).replace("\\", "/"),
                        line=1,
                        rule="LAY005",
                        message=f"Disallowed infrastructure package: '{child.name}'",
                    )
                )
            elif (
                child.is_file()
                and child.name.endswith(".py")
                and child.name != "__init__.py"
            ):
                findings.append(
                    Finding(
                        path=str(child.relative_to(root)).replace("\\", "/"),
                        line=1,
                        rule="LAY005",
                        message=f"Unexpected root file in infrastructure: '{child.name}'. Root files must be inside subpackages.",
                    )
                )

    # Collect production py files only from production layers and backend root
    prod_py_files: list[Path] = [p for p in backend_root.glob("*.py") if p.is_file()]
    for layer in ("domain", "application", "infrastructure", "presentation", "config"):
        layer_dir = backend_root / layer
        if layer_dir.is_dir():
            prod_py_files.extend(
                p
                for p in layer_dir.rglob("*.py")
                if not any(
                    part.startswith((".", "__"))
                    for part in p.relative_to(layer_dir).parts
                )
            )

    for py_file in sorted(prod_py_files):
        relative_path = py_file.relative_to(root)
        posix_path = str(relative_path).replace("\\", "/")
        parts = relative_path.parts  # ('backend', layer, ...)
        layer = parts[1] if len(parts) > 2 else ""

        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=posix_path)
        except (SyntaxError, UnicodeDecodeError) as exc:
            findings.append(
                Finding(
                    path=posix_path,
                    line=getattr(exc, "lineno", 1) or 1,
                    rule="LAY000",
                    message=f"Syntax or decode error: {exc}",
                )
            )
            continue

        module_name = ".".join(relative_path.with_suffix("").parts)
        aliases = _extract_aliases(tree, module_name)

        # LAY004: No legacy backend.storage imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    if "backend.storage" in name.name or name.name == "storage":
                        findings.append(
                            Finding(
                                path=posix_path,
                                line=node.lineno,
                                rule="LAY004",
                                message=f"Legacy 'backend.storage' import is prohibited: {name.name}",
                            )
                        )
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if "backend.storage" in mod or (
                    node.level == 1 and mod.startswith("storage")
                ):
                    findings.append(
                        Finding(
                            path=posix_path,
                            line=node.lineno,
                            rule="LAY004",
                            message=f"Legacy 'backend.storage' import is prohibited: {mod}",
                        )
                    )

        # LAY003: Inner layers technology independence
        if layer in {"domain", "application"}:
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    dependency = _qualified_name(node.func, aliases)
                    method = dependency.rsplit(".", 1)[-1]
                    if method in FILESYSTEM_METHODS:
                        findings.append(
                            Finding(
                                path=posix_path,
                                line=node.lineno,
                                rule="LAY003",
                                message=f"Filesystem method '{method}' is prohibited in inner layer '{layer}'",
                            )
                        )
                    elif dependency.startswith("os.") and method in OS_IO_FUNCTIONS:
                        findings.append(
                            Finding(
                                path=posix_path,
                                line=node.lineno,
                                rule="LAY003",
                                message=f"OS IO function '{dependency}' is prohibited in inner layer '{layer}'",
                            )
                        )
                elif isinstance(node, (ast.Name, ast.Attribute)):
                    dependency = _qualified_name(node, aliases)
                    if dependency == "os.environ" or dependency.startswith(
                        "os.environ."
                    ):
                        findings.append(
                            Finding(
                                path=posix_path,
                                line=node.lineno,
                                rule="LAY003",
                                message=f"Direct access to '{dependency}' is prohibited in inner layer '{layer}'",
                            )
                        )

        # LAY006: Presentation Response DTO boundaries
        if layer == "presentation":
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
                    findings.append(
                        Finding(
                            path=posix_path,
                            line=function.lineno,
                            rule="LAY006",
                            message="Response DTO must not be rehydrated into Application models",
                        )
                    )

    return sorted(findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[2]
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()

    findings = check(root)
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
