"""Adapt Codex events to the shared quality runner; keep checks outside the hook."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.hooks.format_edited_python import edited_paths
from scripts.hooks.format_edited_python import main as format_python
from scripts.hooks.quality_feedback import repair_state, report_feedback

EDIT_WARNING_THRESHOLD = 5


def filter_changed_paths(paths: list[str] | set[str]) -> list[str]:
    return sorted(
        path
        for path in paths
        if path and not path.startswith(("pytest-of-", ".agents/work/"))
    )


def changed_paths(root: Path) -> list[str]:
    paths = set()
    for args in (
        ["diff", "HEAD", "--name-only", "-z", "--no-renames"],
        ["ls-files", "--others", "--exclude-standard", "-z"],
    ):
        output = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, check=True
        ).stdout.decode("utf-8")
        paths.update(output.split("\0"))
    return filter_changed_paths(paths)


def validation_context(root: Path) -> str:
    """Bind receipts to HEAD and the tracked validation configuration."""
    head = (
        subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, check=True
        )
        .stdout.decode("utf-8")
        .strip()
    )
    tracked = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True
    ).stdout.decode("utf-8")
    inputs = [
        name
        for name in tracked.split("\0")
        if name
        and (
            name.endswith((".json", ".toml", ".yaml", ".yml", ".ini", ".lock"))
            or name.startswith(("scripts/checks/", "scripts/hooks/"))
            or Path(name).name.startswith(
                (".python-version", ".nvmrc", ".importlinter")
            )
        )
    ]
    return head + ":" + fingerprint(root, inputs)


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


def edit_state_path(directory: Path, turn: str) -> Path:
    key = hashlib.sha256(turn.encode("utf-8")).hexdigest()[:24]
    return directory / f"{key}.edits.json"


def edit_loop_warnings(root: Path, event: dict, files: list[Path]) -> list[str]:
    if not files:
        return []

    turn = str(event.get("turn_id") or event.get("session_id") or "current")
    directory = root / ".agents/work/.hooks"
    state_path = edit_state_path(directory, turn)
    try:
        stored = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        stored = {}
    if (
        not isinstance(stored, dict)
        or stored.get("version") != 1
        or not isinstance(stored.get("counts"), dict)
    ):
        stored = {}

    counts = {
        name: count
        for name, count in stored.get("counts", {}).items()
        if isinstance(name, str) and type(count) is int and count > 0
    }
    stored_warned = stored.get("warned", [])
    if not isinstance(stored_warned, list):
        stored_warned = []
    warned = {name for name in stored_warned if isinstance(name, str)}
    crossed_threshold = []
    for path in sorted(set(files)):
        try:
            name = path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            continue
        counts[name] = counts.get(name, 0) + 1
        if counts[name] >= EDIT_WARNING_THRESHOLD and name not in warned:
            warned.add(name)
            crossed_threshold.append(name)

    try:
        directory.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps(
                {"version": 1, "counts": counts, "warned": sorted(warned)},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except OSError as error:
        print(f"Could not record edit-loop state: {error}", file=sys.stderr)
        return []
    return crossed_threshold


def archive_edit_state(directory: Path, turn: str, state_path: Path) -> None:
    """Persist cumulative edit counts and loop warnings before deleting active turn state."""
    try:
        stored = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if not isinstance(stored, dict) or stored.get("version") != 1:
        return
    counts = stored.get("counts")
    if not isinstance(counts, dict):
        counts = {}
    total_edits = sum(
        count for count in counts.values() if type(count) is int and count > 0
    )
    warned = stored.get("warned")
    warnings_count = (
        len([name for name in warned if isinstance(name, str)])
        if isinstance(warned, list)
        else 0
    )
    if total_edits <= 0 and warnings_count <= 0:
        return
    turn_key = hashlib.sha256(turn.encode("utf-8")).hexdigest()[:24]
    entry = {
        "version": 1,
        "timestamp": int(time.time() * 1000),
        "turnKey": turn_key,
        "totalEdits": total_edits,
        "editLoopWarnings": warnings_count,
        "filesCount": sum(
            1 for count in counts.values() if type(count) is int and count > 0
        ),
    }
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / "edit-history.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as error:
        print(f"Could not record edit history: {error}", file=sys.stderr)


def clear_edit_state(directory: Path, turn: str) -> None:
    state_path = edit_state_path(directory, turn)
    if state_path.is_file():
        archive_edit_state(directory, turn, state_path)
    try:
        state_path.unlink(missing_ok=True)
    except OSError as error:
        print(f"Could not clear edit-loop state: {error}", file=sys.stderr)


def append_stop_history(
    directory: Path,
    *,
    turn_key: str,
    status: str,
    exit_code: int,
    duration_ms: int,
    attempts: int,
    repeated_failures: int,
    structured: dict | None,
) -> None:
    """Persist per-execution Stop telemetry so multi-attempt repairs are not overwritten."""
    tasks = []
    if isinstance(structured, dict) and isinstance(structured.get("tasks"), list):
        for task in structured["tasks"]:
            if not isinstance(task, dict):
                continue
            tasks.append(
                {
                    "label": task.get("label") or "unknown",
                    "status": task.get("status") or "unknown",
                    "durationMs": task.get("durationMs") or 0,
                }
            )
    entry = {
        "version": 1,
        "timestamp": int(time.time() * 1000),
        "turnKey": turn_key,
        "status": status,
        "result": exit_code,
        "durationMs": duration_ms,
        "attempts": attempts,
        "repeatedFailures": repeated_failures,
        "tasks": tasks,
    }
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / "stop-history.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as error:
        print(f"Could not record stop history: {error}", file=sys.stderr)


def edit_warning_context(paths: list[str]) -> str:
    return "\n".join(
        f"Repeated editing reminder: `{path}` has reached {EDIT_WARNING_THRESHOLD} edits this turn. "
        "Pause to compare the approach with the acceptance criteria and reconsider the plan before editing again. "
        "This is advisory and does not block the work."
        for path in paths
    )


def stop_decision(
    event: dict, signature: str, previous: dict | None, result: int | None
) -> dict:
    if (
        previous
        and previous.get("signature") == signature
        and previous.get("status") in {"stagnated", "attempt_limit"}
    ):
        return {
            "systemMessage": f"Quality repair stopped: {previous['status']}. Unresolved failures remain. Report the log and request a revised diagnosis; do not claim success or weaken checks."
        }
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
        edit_warnings = edit_loop_warnings(ROOT, event, files)
        formatting = format_python(event)
        contexts = []
        if edit_warnings:
            contexts.append(edit_warning_context(edit_warnings))
        if formatting:
            contexts.append("Formatting edited files failed.")
        if contexts:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": "\n\n".join(contexts),
                }
            }
        return {}
    if event.get("hook_event_name") != "Stop":
        return {}

    def signature_for_current_inputs() -> str:
        return hashlib.sha256(
            (
                validation_context(ROOT)
                + fingerprint(ROOT, changed_paths(ROOT))
                + fingerprint(ROOT, ["tmp/quality/task.json"])
            ).encode("utf-8")
        ).hexdigest()

    signature = signature_for_current_inputs()
    spec_signature = fingerprint(ROOT, ["tmp/quality/task.json"])
    turn = str(event.get("turn_id") or event.get("session_id") or "current")
    key = hashlib.sha256(turn.encode("utf-8")).hexdigest()[:24]
    directory = ROOT / ".agents/work/.hooks"
    directory.mkdir(parents=True, exist_ok=True)

    def finish_stop(decision: dict) -> dict:
        if decision.get("decision") != "block":
            clear_edit_state(directory, turn)
        return decision

    receipt = directory / f"{key}.json"
    try:
        if receipt.exists():
            previous = json.loads(receipt.read_text(encoding="utf-8"))
        else:
            previous = None
            for candidate_path in sorted(directory.glob("*.json")):
                if any(
                    candidate_path.name.endswith(suffix)
                    for suffix in (
                        ".report.json",
                        ".edits.json",
                        ".quality-feedback.json",
                        ".quality-stop.json",
                        ".privacy.json",
                    )
                ):
                    continue
                try:
                    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
                except (ValueError, OSError):
                    continue
                if (
                    isinstance(candidate, dict)
                    and candidate.get("signature") == signature
                    and candidate.get("result") == 0
                    and candidate.get("status") == "passed"
                ):
                    previous = candidate
                    break
        if not isinstance(previous, dict):
            previous = None
    except (ValueError, OSError):
        print("Invalid quality receipt; running checks again.", file=sys.stderr)
        previous = None
    if (
        previous
        and previous.get("signature") == signature
        and (
            previous.get("result") == 0
            or event.get("stop_hook_active")
            or previous.get("status") in {"stagnated", "attempt_limit"}
        )
    ):
        return finish_stop(stop_decision(event, signature, previous, None))
    log = directory / f"{key}.log"
    report = directory / f"{key}.report.json"
    report.unlink(missing_ok=True)
    started_at = time.monotonic()
    with log.open("w", encoding="utf-8") as output:
        try:
            exit_code = subprocess.run(
                [
                    "node",
                    str(ROOT / "scripts/checks/quality.mjs"),
                    "--changed",
                    "--report",
                    str(report),
                    "--require-spec",
                    "--phase",
                    "quick",
                    "--parallel",
                ],
                cwd=ROOT,
                stdout=output,
                stderr=subprocess.STDOUT,
                timeout=540,
                check=False,
            ).returncode
            status = "passed" if exit_code == 0 else "failed"
        except (OSError, subprocess.TimeoutExpired) as error:
            output.write(f"Quality runner failed: {error}\n")
            exit_code = 1
            status = (
                "timeout"
                if isinstance(error, subprocess.TimeoutExpired)
                else "start_error"
            )
    duration_ms = int((time.monotonic() - started_at) * 1000)
    # A check must not certify files changed during execution (including generated output).
    if signature_for_current_inputs() != signature:
        exit_code = 1
        status = "inputs_changed"
        with log.open("a", encoding="utf-8") as output:
            output.write(
                "Files changed during validation; rerun against the current contents.\n"
            )
    try:
        structured = (
            json.loads(report.read_text(encoding="utf-8")) if report.exists() else None
        )
        if not isinstance(structured, dict):
            structured = None
    except (ValueError, OSError):
        structured = None
    failure_key, feedback = report_feedback(structured)
    state = repair_state(
        previous
        if previous and previous.get("spec_signature") == spec_signature
        else None,
        exit_code,
        failure_key if status == "failed" else None,
    )
    if state.get("terminal"):
        status = state["terminal"]
    current = {
        "signature": signature,
        "spec_signature": spec_signature,
        "result": exit_code,
        "status": status,
        "log": log.name,
        "report": report.name if report.exists() else None,
        **state,
    }
    receipt.write_text(
        json.dumps(current),
        encoding="utf-8",
    )
    append_stop_history(
        directory,
        turn_key=key,
        status=status,
        exit_code=exit_code,
        duration_ms=duration_ms,
        attempts=int(state.get("attempts", 0)),
        repeated_failures=int(state.get("repeated_failures", 0)),
        structured=structured,
    )
    if state.get("terminal"):
        return finish_stop(stop_decision(event, signature, current, exit_code))
    decision = stop_decision(event, signature, previous, exit_code)
    if decision.get("decision") == "block":
        decision["reason"] += f"\nLog: {log.relative_to(ROOT).as_posix()}\n{feedback}"
    return finish_stop(decision)


if __name__ == "__main__":
    try:
        print(json.dumps(main(json.load(sys.stdin)), ensure_ascii=False))
    except Exception as error:
        print(f"Quality hook failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
