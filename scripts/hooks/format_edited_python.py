"""Format edited Python and Frontend files explicitly touched by a Codex/Antigravity tool."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

FRONTEND_EXTENSIONS = {
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".json",
    ".css",
}


def edited_paths(event: dict) -> list[Path]:
    tool = event.get("tool_name", "")
    data = event.get("tool_input", {})
    tool = tool.rsplit(".", 1)[-1]
    if tool not in {"apply_patch", "Edit", "Write"}:
        return []
    paths = []
    if tool == "apply_patch":
        patch = (
            data
            if isinstance(data, str)
            else data.get("command", data.get("patch", ""))
            if isinstance(data, dict)
            else ""
        )
        if not isinstance(patch, str):
            return []
        for line in patch.splitlines():
            for prefix in ("*** Add File: ", "*** Update File: ", "*** Move to: "):
                if line.startswith(prefix):
                    paths.append(line.removeprefix(prefix))
    else:
        path = data.get("file_path") if isinstance(data, dict) else None
        if isinstance(path, str):
            paths.append(path)
    cwd = Path(event.get("cwd", str(ROOT)))
    files = set()
    for value in paths:
        path = Path(value)
        path = (path if path.is_absolute() else cwd / path).resolve()
        if path.is_relative_to(ROOT) and path.is_file():
            files.add(path)
    return sorted(files)


def edited_files(event: dict) -> list[Path]:
    return [path for path in edited_paths(event) if path.suffix == ".py"]


def edited_frontend_files(event: dict) -> list[Path]:
    return [
        path
        for path in edited_paths(event)
        if path.suffix in FRONTEND_EXTENSIONS
        and (
            path.is_relative_to(ROOT / "frontend")
            or path.is_relative_to(ROOT / "scripts")
        )
    ]


def format_python_files(files: list[Path]) -> int:
    if not files:
        return 0
    ruff_bin = (
        ROOT
        / "backend/.venv"
        / ("Scripts/ruff.exe" if sys.platform == "win32" else "bin/ruff")
    )
    if ruff_bin.is_file():
        ruff = [str(ruff_bin)]
    else:
        python = (
            ROOT
            / "backend/.venv"
            / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        )
        ruff = [str(python), "-m", "ruff"]

    results = []
    for args in (("check", "--fix"), ("format",)):
        result = subprocess.run(
            [*ruff, *args, *map(str, files)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=45,
            check=False,
        )
        results.append(result.returncode)
        if result.returncode:
            print(result.stdout + result.stderr, file=sys.stderr)
    return int(any(results))


def format_frontend_files(files: list[Path]) -> int:
    if not files:
        return 0
    frontend_files = [
        str(f.relative_to(ROOT / "frontend").as_posix())
        for f in files
        if f.is_relative_to(ROOT / "frontend")
    ]
    if not frontend_files:
        return 0
    pnpm_cmd = "pnpm.cmd" if sys.platform == "win32" else "pnpm"
    result = subprocess.run(
        [
            pnpm_cmd,
            "--filter",
            "frontend",
            "exec",
            "biome",
            "format",
            "--write",
            *frontend_files,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=45,
        check=False,
    )
    if result.returncode:
        print(result.stdout + result.stderr, file=sys.stderr)
    return result.returncode


def main(event: dict | None = None) -> int:
    evt = json.load(sys.stdin) if event is None else event
    py_files = edited_files(evt)
    fe_files = edited_frontend_files(evt)
    py_code = format_python_files(py_files)
    fe_code = format_frontend_files(fe_files)
    return int(py_code != 0 or fe_code != 0)


if __name__ == "__main__":
    raise SystemExit(main())
