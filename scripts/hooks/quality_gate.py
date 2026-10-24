"""Adapt Codex events to the shared quality runner; keep checks outside the hook."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.hooks.format_edited_python import edited_paths
from scripts.hooks.format_edited_python import main as format_python


def changed_paths(root: Path) -> list[str]:
    paths = set()
    for args in (
        ["diff", "HEAD", "--name-only", "-z", "--no-renames"],
        ["ls-files", "--others", "--exclude-standard", "-z"],
    ):
        result = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, check=True
        )
        paths.update(result.stdout.decode("utf-8").split("\0"))
    return sorted(path for path in paths if path)


def fingerprint(root: Path, paths: list[str]) -> str:
    digest = hashlib.sha256()
    for name in paths:
        digest.update(name.encode("utf-8") + b"\0")
        path = root / name
        if path.is_file():
            digest.update(path.read_bytes())
        else:
            digest.update(b"<deleted>")
        digest.update(b"\0")
    return digest.hexdigest()


def stop_decision(
    event: dict, signature: str, previous: dict | None, result: int | None
) -> dict:
    if previous and previous.get("signature") == signature:
        if previous.get("result") == 0:
            return {}
        if event.get("stop_hook_active"):
            return {
                "systemMessage": "Quality checks still fail. Report failures and the log; do not claim success."
            }
    if result is None or result == 0:
        return {}
    return {
        "decision": "block",
        "reason": "Quality checks failed. Inspect .agents/work/.hooks logs, fix scoped failures, and rerun. Report environment blockers explicitly.",
    }


def main(event: dict) -> dict:
    if event.get("hook_event_name") == "PostToolUse":
        files = edited_paths(event)
        if not files:
            return {}
        formatting = format_python(event)
        scopes = set()
        for path in files:
            name = path.relative_to(ROOT).as_posix()
            if path.suffix == ".py":
                scopes.add("backend")
            if name.startswith("frontend/"):
                scopes.add("frontend")
            if name.startswith("scripts/"):
                scopes.add("scripts")
        failures = ["Formatting edited Python files failed."] if formatting else []
        for scope in sorted(scopes):
            quick_process = subprocess.run(
                [
                    "node",
                    str(ROOT / "scripts/checks/quality.mjs"),
                    "--scope",
                    scope,
                    "--phase",
                    "quick",
                ],
                cwd=ROOT,
                capture_output=True,
                timeout=180,
                check=False,
            )
            if quick_process.returncode:
                failures.append(
                    (quick_process.stdout + quick_process.stderr).decode(
                        "utf-8", errors="replace"
                    )
                )
        if failures:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": "Quick checks failed:\n"
                    + "\n".join(failures)[-12000:],
                }
            }
        return {}
    if event.get("hook_event_name") != "Stop":
        return {}
    paths = changed_paths(ROOT)
    signature = fingerprint(ROOT, paths)
    turn = str(event.get("turn_id") or event.get("session_id") or "current")
    key = hashlib.sha256(turn.encode("utf-8")).hexdigest()[:24]
    directory = ROOT / ".agents/work/.hooks"
    directory.mkdir(parents=True, exist_ok=True)
    receipt = directory / f"{key}.json"
    previous = (
        json.loads(receipt.read_text(encoding="utf-8")) if receipt.exists() else None
    )
    if (
        previous
        and previous.get("signature") == signature
        and (previous.get("result") == 0 or event.get("stop_hook_active"))
    ):
        return stop_decision(event, signature, previous, None)
    log = directory / f"{key}.log"
    with log.open("w", encoding="utf-8") as output:
        try:
            exit_code = subprocess.run(
                ["node", str(ROOT / "scripts/checks/quality.mjs"), "--changed"],
                cwd=ROOT,
                stdout=output,
                stderr=subprocess.STDOUT,
                timeout=540,
                check=False,
            ).returncode
        except (OSError, subprocess.TimeoutExpired) as error:
            output.write(f"Quality runner failed: {error}\n")
            exit_code = 1
    # A check must not certify files changed during execution (including generated output).
    if fingerprint(ROOT, changed_paths(ROOT)) != signature:
        exit_code = 1
        with log.open("a", encoding="utf-8") as output:
            output.write(
                "Files changed during validation; rerun against the current contents.\n"
            )
    receipt.write_text(
        json.dumps({"signature": signature, "result": exit_code}), encoding="utf-8"
    )
    return stop_decision(event, signature, previous, exit_code)


if __name__ == "__main__":
    try:
        print(json.dumps(main(json.load(sys.stdin)), ensure_ascii=False))
    except Exception as error:
        print(f"Quality hook failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
