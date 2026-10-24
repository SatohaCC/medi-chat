"""Format only Python files explicitly edited by a Codex file-edit tool."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def edited_files(event: dict) -> list[Path]:
    tool = event.get("tool_name", "")
    data = event.get("tool_input", {})
    if tool not in {"apply_patch", "Edit", "Write"} or not isinstance(data, dict):
        return []
    paths = []
    if tool == "apply_patch":
        patch = data.get("command", "")
        if not isinstance(patch, str):
            return []
        for line in patch.splitlines():
            for prefix in ("*** Add File: ", "*** Update File: ", "*** Move to: "):
                if line.startswith(prefix):
                    paths.append(line.removeprefix(prefix))
    else:
        path = data.get("file_path")
        if isinstance(path, str):
            paths.append(path)
    cwd = Path(event.get("cwd", str(ROOT)))
    files = set()
    for value in paths:
        path = Path(value)
        path = (path if path.is_absolute() else cwd / path).resolve()
        if path.is_relative_to(ROOT) and path.suffix == ".py" and path.is_file():
            files.add(path)
    return sorted(files)


def main() -> int:
    files = edited_files(json.load(sys.stdin))
    if not files:
        return 0
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


if __name__ == "__main__":
    raise SystemExit(main())
