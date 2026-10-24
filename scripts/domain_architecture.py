"""Static Domain harness. Inspected source is parsed, never imported or executed."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

ROLES = {
    "identifiers": set(),
    "exceptions": set(),
    "primitives": {"exceptions"},
    "value_objects": {"identifiers", "exceptions", "primitives"},
    "entities": {"identifiers", "exceptions", "primitives", "value_objects"},
    "repositories": {
        "identifiers",
        "exceptions",
        "primitives",
        "value_objects",
        "entities",
    },
    "services": {
        "identifiers",
        "exceptions",
        "primitives",
        "value_objects",
        "entities",
        "repositories",
    },
}
VALUE_MODULES = {
    "__future__",
    "abc",
    "array",
    "base64",
    "bisect",
    "builtins",
    "calendar",
    "collections",
    "copy",
    "dataclasses",
    "datetime",
    "decimal",
    "enum",
    "fractions",
    "functools",
    "hashlib",
    "heapq",
    "hmac",
    "itertools",
    "keyword",
    "math",
    "numbers",
    "operator",
    "re",
    "statistics",
    "string",
    "types",
    "typing",
    "unicodedata",
    "urllib",
    "uuid",
}
MUTABLE = {
    "list",
    "dict",
    "set",
    "bytearray",
    "List",
    "Dict",
    "Set",
    "MutableMapping",
    "MutableSequence",
    "MutableSet",
    "DefaultDict",
    "Deque",
    "deque",
    "defaultdict",
    "Counter",
}
RAW = {"str", "int", "float", "bytes", "Any", "object"}
ID_BASES = {
    "backend.domain.foundation.primitives.identifiers.EntityStringId",
    "backend.domain.foundation.primitives.identifiers.EntityUUID",
}
PRIMITIVE_BASE = "backend.domain.foundation.primitives.base.DomainPrimitive"


@dataclass(frozen=True, order=True)
class Finding:
    path: str
    line: int
    rule: str
    message: str


@dataclass
class Source:
    path: Path
    module: str
    context: str
    role: str
    tree: ast.Module
    aliases: dict[str, str]
    types: dict[str, ast.AST]

    def name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return self.aliases.get(node.id, node.id)
        if isinstance(node, ast.Attribute):
            return self.name(node.value) + "." + node.attr
        if isinstance(node, ast.Subscript):
            return self.name(node.value)
        if isinstance(node, ast.Call):
            return self.name(node.func)
        return ""

    def annotation_names(
        self, node: ast.AST, seen: frozenset[str] = frozenset()
    ) -> set[str]:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            try:
                return self.annotation_names(
                    ast.parse(node.value, mode="eval").body, seen
                )
            except SyntaxError:
                return set()
        name = self.name(node)
        result = {name} if name else set()
        if isinstance(node, ast.Name) and node.id in self.types and node.id not in seen:
            result.update(self.annotation_names(self.types[node.id], seen | {node.id}))
        for child in ast.iter_child_nodes(node):
            result.update(self.annotation_names(child, seen))
        return result


def imported_names(
    source: Source, node: ast.Import | ast.ImportFrom
) -> list[tuple[str, str]]:
    if isinstance(node, ast.Import):
        return [
            (
                item.asname or item.name.split(".")[0],
                item.name if item.asname else item.name.split(".")[0],
            )
            for item in node.names
        ]
    base = node.module or ""
    if node.level:
        package = source.module.split(".")[:-1]
        base = ".".join(
            package[: len(package) - node.level + 1] + ([base] if base else [])
        )
    return [
        (item.asname or item.name, f"{base}.{item.name}" if base else item.name)
        for item in node.names
    ]


def check(root: Path, *, context: str | None = None) -> list[Finding]:
    root = root.resolve()
    domain = root / "backend/domain"
    if not domain.is_dir():
        raise ValueError(f"Domain directory not found: {domain}")
    contexts = {
        p.name
        for p in domain.iterdir()
        if p.is_dir() and not p.name.startswith((".", "__"))
    }
    if context is not None and context not in contexts:
        raise ValueError(f"Unknown Domain context: {context}")
    findings: list[Finding] = []

    def emit(path: Path, node: ast.AST | int, rule: str, message: str) -> None:
        relative = path.relative_to(domain)
        if context is None or relative.parts[0] == context:
            findings.append(
                Finding(
                    path.relative_to(root).as_posix(),
                    node if isinstance(node, int) else getattr(node, "lineno", 1),
                    rule,
                    message,
                )
            )

    if not (domain / "__init__.py").is_file():
        emit(domain / "__init__.py", 1, "DOM001", "Domain packages require __init__.py")
    for directory in sorted(p for p in domain.rglob("*") if p.is_dir()):
        parts = directory.relative_to(domain).parts
        if any(part.startswith((".", "__")) for part in parts):
            continue
        if len(parts) > 1 and parts != ("foundation", "primitives"):
            emit(directory, 1, "DOM001", "Nested Domain packages are forbidden")
        if not (directory / "__init__.py").is_file():
            emit(
                directory / "__init__.py",
                1,
                "DOM001",
                "Domain packages require __init__.py",
            )

    sources = []
    for path in sorted(domain.rglob("*.py")):
        relative = path.relative_to(domain)
        if "__pycache__" in relative.parts:
            continue
        parts = relative.with_suffix("").parts
        ctx = parts[0] if len(parts) > 1 else ""
        role = parts[1] if len(parts) > 1 else "__init__"
        valid = (
            (len(parts) == 1 and parts[0] == "__init__")
            or (
                len(parts) == 2
                and (
                    role in ROLES
                    or role == "__init__"
                    or (ctx == "foundation" and role == "json_types")
                )
            )
            or (
                ctx == "foundation"
                and len(parts) == 3
                and parts[1] == "primitives"
                and parts[2]
                in {"__init__", "base", "primitives", "identifiers", "enums"}
            )
        )
        if not valid:
            emit(
                path,
                1,
                "DOM001",
                "Use canonical flat Domain modules; only foundation/primitives may be nested",
            )
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            emit(path, exc.lineno or 1, "DOM000", str(exc.msg))
            continue
        source = Source(
            path, "backend.domain." + ".".join(parts), ctx, role, tree, {}, {}
        )
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                source.aliases.update(imported_names(source, node))
            elif isinstance(node, ast.TypeAlias):
                source.types[node.name.id] = node.value
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                source.aliases[node.name] = source.module + "." + node.name
            elif (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
            ):
                source.types[node.targets[0].id] = node.value
                if isinstance(node.value, (ast.Name, ast.Attribute)):
                    source.aliases[node.targets[0].id] = source.name(node.value)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.value is not None
                and source.name(node.annotation) == "typing.TypeAlias"
            ):
                source.types[node.target.id] = node.value
        if path.name == "__init__.py" and any(
            not (
                isinstance(n, ast.Expr)
                and isinstance(n.value, ast.Constant)
                and isinstance(n.value.value, str)
            )
            for n in tree.body
        ):
            emit(
                path,
                1,
                "DOM002",
                "Package initializers must be empty or docstring-only",
            )
        sources.append(source)

    classes = {
        s.module + "." + n.name: (s, n)
        for s in sources
        for n in s.tree.body
        if isinstance(n, ast.ClassDef)
    }
    type_symbols = {
        s.module + "." + name: (s, value)
        for s in sources
        for name, value in s.types.items()
    }

    def field_names(source: Source, annotation: ast.AST) -> set[str]:
        names = source.annotation_names(annotation)
        pending = list(names)
        while pending:
            name = pending.pop()
            if name in type_symbols:
                owner, value = type_symbols[name]
                resolved = owner.annotation_names(value) - names
                names.update(resolved)
                pending.extend(resolved)
        return names

    def inherits(
        name: str, targets: set[str], seen: frozenset[str] = frozenset()
    ) -> bool:
        if name in targets:
            return True
        if name in seen or name not in classes:
            return False
        s, cls = classes[name]
        return any(inherits(s.name(b), targets, seen | {name}) for b in cls.bases)

    def frozen(name: str, seen: frozenset[str] = frozenset()) -> bool:
        if name == PRIMITIVE_BASE and name not in classes:
            return True
        if name in seen or name not in classes:
            return False
        s, cls = classes[name]
        for dec in cls.decorator_list:
            if s.name(dec) == "dataclasses.dataclass":
                return isinstance(dec, ast.Call) and any(
                    kw.arg == "frozen"
                    and isinstance(kw.value, ast.Constant)
                    and kw.value.value is True
                    for kw in dec.keywords
                )
        return any(frozen(s.name(b), seen | {name}) for b in cls.bases)

    for ctx in sorted(contexts - {"foundation", "shared"}):
        path = domain / ctx / "identifiers.py"
        id_source = next((s for s in sources if s.path == path), None)
        definitions = (
            [n for n in id_source.tree.body if isinstance(n, ast.ClassDef)]
            if id_source
            else []
        )
        if (
            id_source is None
            or len(definitions) != 1
            or not inherits(id_source.module + "." + definitions[0].name, ID_BASES)
        ):
            emit(
                path,
                1,
                "DOM005",
                "Each business context must define exactly one public ID inheriting EntityStringId or EntityUUID",
            )
        if id_source:
            for node in id_source.tree.body:
                if isinstance(
                    node,
                    (
                        ast.FunctionDef,
                        ast.AsyncFunctionDef,
                        ast.Assign,
                        ast.AnnAssign,
                        ast.TypeAlias,
                    ),
                ):
                    emit(
                        path,
                        node,
                        "DOM005",
                        "Public ID modules must not expose other values or operations",
                    )

    def validate_dependency(s: Source, node: ast.AST, target: str) -> None:
        if target.endswith(".*"):
            emit(s.path, node, "DOM006", "Wildcard imports are forbidden")
        top = target.split(".")[0]
        if target.startswith("backend.domain."):
            parts = target.split(".")
            target_ctx = parts[2]
            target_role = parts[3] if len(parts) > 3 else ""
            if s.role == "identifiers" and s.context != "foundation":
                if (
                    target != "backend.domain.foundation.primitives.identifiers"
                    and not target.startswith(
                        "backend.domain.foundation.primitives.identifiers."
                    )
                ):
                    emit(
                        s.path,
                        node,
                        "DOM005",
                        "Public IDs may import only the foundation ID base and standard library",
                    )
            elif s.context == "foundation" and target_ctx != "foundation":
                emit(
                    s.path,
                    node,
                    "DOM003",
                    "Foundation cannot depend on other contexts",
                )
            elif s.context == "shared" and target_ctx not in {
                "foundation",
                "shared",
            }:
                emit(
                    s.path,
                    node,
                    "DOM003",
                    "Shared cannot depend on business contexts",
                )
            elif (
                target_ctx not in {s.context, "foundation", "shared"}
                and target_role != "identifiers"
            ):
                emit(
                    s.path,
                    node,
                    "DOM003",
                    "Cross-context imports may use public identifiers only",
                )
            elif target_ctx in {s.context, "shared"} and s.role in ROLES:
                permitted = ROLES[s.role] | {s.role}
                if (
                    target_ctx == "shared"
                    and target_role == "services"
                    and s.role in {"entities", "repositories", "services"}
                ):
                    return
                if target_role not in permitted:
                    emit(
                        s.path,
                        node,
                        "DOM004",
                        f"{s.role} cannot depend on {target_role or 'a context package'}",
                    )
        elif top == "backend":
            emit(s.path, node, "DOM003", f"Domain cannot depend on {target}")
        elif top not in VALUE_MODULES or (
            top == "urllib"
            and not (target == "urllib.parse" or target.startswith("urllib.parse."))
        ):
            emit(
                s.path,
                node,
                "DOM006",
                f"External or technical dependency: {target}",
            )

    for s in sources:
        for node in ast.walk(s.tree):
            annotations = []
            if isinstance(node, (ast.arg, ast.AnnAssign)):
                annotations = [node.annotation] if node.annotation else []
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                annotations = [node.returns] if node.returns else []
            elif isinstance(node, ast.TypeAlias):
                annotations = [node.value]
            for annotation in annotations:
                for target in field_names(s, annotation):
                    if target.startswith("backend."):
                        validate_dependency(s, node, target)
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                targets = (
                    [n.name for n in node.names]
                    if isinstance(node, ast.Import)
                    else [name for _, name in imported_names(s, node)]
                )
                for target in targets:
                    validate_dependency(s, node, target)
            elif isinstance(node, ast.Call):
                if s.name(node.func) in {
                    "open",
                    "builtins.open",
                    "eval",
                    "builtins.eval",
                    "exec",
                    "builtins.exec",
                    "__import__",
                    "builtins.__import__",
                    "input",
                    "builtins.input",
                    "print",
                    "builtins.print",
                    "breakpoint",
                    "builtins.breakpoint",
                }:
                    emit(
                        s.path,
                        node,
                        "DOM006",
                        "File access and dynamic execution are forbidden",
                    )
            elif (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "create"
            ):
                emit(
                    s.path,
                    node,
                    "DOM010",
                    "Construct typed Domain models directly instead of create wrappers",
                )
            elif isinstance(node, ast.ClassDef) and node not in s.tree.body:
                emit(
                    s.path,
                    node,
                    "DOM012",
                    "Define Domain classes at module scope so their role is explicit",
                )
        for cls in (n for n in s.tree.body if isinstance(n, ast.ClassDef)):
            name = s.module + "." + cls.name
            model = s.role in {"entities", "value_objects"} and s.context not in {
                "foundation",
                "shared",
            }
            decorated = any(
                s.name(dec) == "dataclasses.dataclass" for dec in cls.decorator_list
            )
            if (model or decorated) and not frozen(name):
                emit(
                    s.path,
                    cls,
                    "DOM007",
                    "Domain data models must be frozen dataclasses",
                )
            if (
                s.role == "primitives"
                and s.context not in {"foundation", "shared"}
                and not inherits(name, {PRIMITIVE_BASE})
            ):
                emit(
                    s.path,
                    cls,
                    "DOM012",
                    "Domain primitives must inherit DomainPrimitive",
                )
            if s.role == "repositories" and not inherits(name, {"typing.Protocol"}):
                emit(s.path, cls, "DOM012", "Repository contracts must be Protocols")
            for member in cls.body:
                if model and isinstance(member, ast.Assign):
                    emit(
                        s.path,
                        member,
                        "DOM009",
                        "Declare typed fields or explicit ClassVar constants",
                    )
                if isinstance(member, ast.AnnAssign):
                    names = field_names(s, member.annotation)
                    if any(n in {"typing.ClassVar", "ClassVar"} for n in names):
                        continue
                    if any(n.rsplit(".", 1)[-1] in MUTABLE for n in names):
                        emit(
                            s.path,
                            member,
                            "DOM008",
                            "Use immutable field collections, including nested and aliased types",
                        )
                    if model and any(n.rsplit(".", 1)[-1] in RAW for n in names):
                        emit(
                            s.path,
                            member,
                            "DOM009",
                            "Use typed Primitive/VO fields; bool flags are allowed",
                        )
                    if model and member.value is not None:
                        for default in ast.walk(member.value):
                            if isinstance(default, (ast.List, ast.Dict, ast.Set)) or (
                                isinstance(default, ast.keyword)
                                and default.arg == "default_factory"
                                and s.name(default.value).rsplit(".", 1)[-1] in MUTABLE
                            ):
                                emit(
                                    s.path,
                                    member,
                                    "DOM008",
                                    "Field defaults must be immutable",
                                )
                elif model and isinstance(
                    member, (ast.FunctionDef, ast.AsyncFunctionDef)
                ):
                    if member.name.startswith("_require"):
                        emit(
                            s.path,
                            member,
                            "DOM011",
                            "Do not add runtime type-check helpers to typed models",
                        )
                    if member.name == "__post_init__":
                        for operation in ast.walk(member):
                            if isinstance(
                                operation, (ast.Assign, ast.AnnAssign, ast.AugAssign)
                            ):
                                assignment_targets = (
                                    operation.targets
                                    if isinstance(operation, ast.Assign)
                                    else [operation.target]
                                )
                                if any(
                                    isinstance(t, ast.Attribute)
                                    and isinstance(t.value, ast.Name)
                                    and t.value.id == "self"
                                    for t in assignment_targets
                                ):
                                    emit(
                                        s.path,
                                        operation,
                                        "DOM011",
                                        "Post-init must not replace typed fields",
                                    )
                            if (
                                isinstance(operation, ast.Call)
                                and s.name(operation.func)
                                in {"isinstance", "builtins.isinstance"}
                                and operation.args
                            ):
                                value = operation.args[0]
                                if (
                                    isinstance(value, ast.Attribute)
                                    and isinstance(value.value, ast.Name)
                                    and value.value.id == "self"
                                ):
                                    emit(
                                        s.path,
                                        operation,
                                        "DOM011",
                                        "Single-field runtime type checks belong at the input boundary",
                                    )
                            if isinstance(operation, ast.Call) and s.name(
                                operation.func
                            ) in {"object.__setattr__", "setattr", "builtins.setattr"}:
                                emit(
                                    s.path,
                                    operation,
                                    "DOM011",
                                    "Build typed values before model construction; post-init must not replace fields",
                                )

    modules = {s.module.removesuffix(".__init__"): s for s in sources}
    edges: dict[str, set[str]] = {name: set() for name in modules}
    for name, source in modules.items():
        for node in ast.walk(source.tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                targets = (
                    [n.name for n in node.names]
                    if isinstance(node, ast.Import)
                    else [target for _, target in imported_names(source, node)]
                )
                for target in targets:
                    candidates = [
                        key
                        for key in modules
                        if target == key or target.startswith(key + ".")
                    ]
                    if candidates:
                        edges[name].add(max(candidates, key=len))
    visited: set[str] = set()
    active: list[str] = []

    def visit(name: str) -> None:
        if name in active:
            emit(
                modules[name].path,
                1,
                "DOM013",
                "Domain dependency cycle: "
                + " -> ".join(active[active.index(name) :] + [name]),
            )
            return
        if name in visited:
            return
        active.append(name)
        for target in sorted(edges[name]):
            visit(target)
        active.pop()
        visited.add(name)

    for name in sorted(modules):
        visit(name)
    return sorted(set(findings))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--context")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        findings = check(args.root, context=args.context)
    except (OSError, ValueError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps([asdict(f) for f in findings], ensure_ascii=False))
    else:
        for f in findings:
            print(f"{f.path}:{f.line}: {f.rule} {f.message}")
        print(
            f"{len(findings)} findings; {dict(sorted(Counter(f.rule for f in findings).items()))}"
        )
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
