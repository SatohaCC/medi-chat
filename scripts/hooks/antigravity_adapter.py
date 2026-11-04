"""Adapt Antigravity lifecycle events to shared quality and privacy checks."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def handle_quality_post_tool(payload: dict) -> dict:
    tool_call = payload.get("toolCall", {})
    tool_name = tool_call.get("name", "")
    args = tool_call.get("args", {})
    file_path = args.get("Path") or args.get("path") or args.get("filePath")
    codex_tool = (
        "Edit"
        if tool_name == "edit_file"
        else ("Write" if tool_name == "write_file" else tool_name)
    )
    codex_event = {
        "hook_event_name": "PostToolUse",
        "tool_name": codex_tool,
        "tool_input": {"file_path": file_path} if file_path else args,
        "cwd": str(ROOT),
        "turn_id": str(payload.get("conversationId") or "current"),
    }
    from scripts.hooks import quality_gate

    quality_gate.main(codex_event)
    return {}


def handle_privacy_post_tool(payload: dict) -> dict:
    tool_call = payload.get("toolCall", {})
    tool_name = tool_call.get("name", "")
    codex_tool = (
        "Bash"
        if tool_name == "run_command"
        else ("Edit" if tool_name == "edit_file" else "Write")
    )
    codex_event = {
        "hook_event_name": "PostToolUse",
        "tool_name": codex_tool,
        "tool_input": tool_call.get("args", {}),
        "cwd": str(ROOT),
        "turn_id": str(payload.get("conversationId") or "current"),
    }
    from scripts.hooks import privacy_gate

    decision = privacy_gate.main(codex_event)
    if decision and "additionalContext" in decision.get("hookSpecificOutput", {}):
        print(decision["hookSpecificOutput"]["additionalContext"], file=sys.stderr)
    return {}


def handle_quality_stop(payload: dict) -> dict:
    turn_id = str(
        payload.get("conversationId") or payload.get("executionNum") or "current"
    )
    codex_event = {
        "hook_event_name": "Stop",
        "turn_id": turn_id,
        "stop_hook_active": False,
    }
    from scripts.hooks import quality_gate

    quality_decision = quality_gate.main(codex_event)
    if quality_decision.get("decision") == "block":
        return {
            "decision": "continue",
            "reason": quality_decision.get("reason", "Quality checks failed."),
        }
    return {}


def handle_privacy_stop(payload: dict) -> dict:
    turn_id = str(
        payload.get("conversationId") or payload.get("executionNum") or "current"
    )
    codex_event = {
        "hook_event_name": "Stop",
        "turn_id": turn_id,
        "stop_hook_active": False,
    }
    from scripts.hooks import privacy_gate

    privacy_decision = privacy_gate.main(codex_event)
    if privacy_decision.get("decision") == "block":
        return {
            "decision": "continue",
            "reason": privacy_decision.get("reason", "Privacy check failed."),
        }
    return {}


def main(action: str | None = None) -> dict:
    try:
        raw_input = sys.stdin.read()
        payload = json.loads(raw_input) if raw_input.strip() else {}
    except (ValueError, OSError):
        payload = {}

    if not action:
        if "toolCall" in payload:
            action = "post-tool-use"
        elif "terminationReason" in payload or "fullyIdle" in payload:
            action = "stop"
        else:
            action = "stop"

    if action in ("quality-post-tool",):
        return handle_quality_post_tool(payload)
    if action in ("privacy-post-tool",):
        return handle_privacy_post_tool(payload)
    if action in ("quality-stop",):
        return handle_quality_stop(payload)
    if action in ("privacy-stop",):
        return handle_privacy_stop(payload)
    if action in ("post-tool-use", "PostToolUse"):
        handle_quality_post_tool(payload)
        handle_privacy_post_tool(payload)
        return {}
    if action in ("stop", "Stop"):
        privacy_res = handle_privacy_stop(payload)
        if privacy_res.get("decision") == "continue":
            return privacy_res
        return handle_quality_stop(payload)
    return {}


if __name__ == "__main__":
    event_arg = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        result = main(event_arg)
        print(json.dumps(result, ensure_ascii=False))
    except Exception as error:
        print(f"Antigravity hook error: {error}", file=sys.stderr)
        print(json.dumps({}))
        raise SystemExit(1) from error
