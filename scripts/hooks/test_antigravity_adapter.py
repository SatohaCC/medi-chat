from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.hooks import antigravity_adapter as adapter

ROOT = Path(__file__).resolve().parents[2]


def test_quality_post_tool_translates_edit_file(monkeypatch):
    captured_events = []

    def mock_quality_main(event):
        captured_events.append(event)
        return {}

    from scripts.hooks import quality_gate

    monkeypatch.setattr(quality_gate, "main", mock_quality_main)

    payload = {
        "toolCall": {
            "name": "edit_file",
            "args": {"Path": "backend/test.py", "Target": "a", "Replacement": "b"},
        },
        "stepIdx": 2,
        "conversationId": "conv-123",
    }

    result = adapter.handle_quality_post_tool(payload)
    assert result == {}
    assert len(captured_events) == 1
    event = captured_events[0]
    assert event["hook_event_name"] == "PostToolUse"
    assert event["tool_name"] == "Edit"
    assert event["tool_input"]["file_path"] == "backend/test.py"
    assert event["turn_id"] == "conv-123"


def test_quality_post_tool_translates_write_file(monkeypatch):
    captured_events = []

    def mock_quality_main(event):
        captured_events.append(event)
        return {}

    from scripts.hooks import quality_gate

    monkeypatch.setattr(quality_gate, "main", mock_quality_main)

    payload = {
        "toolCall": {
            "name": "write_file",
            "args": {"Path": "scripts/sample.py", "Content": "# test"},
        },
        "stepIdx": 1,
    }

    result = adapter.handle_quality_post_tool(payload)
    assert result == {}
    assert len(captured_events) == 1
    assert captured_events[0]["tool_name"] == "Write"
    assert captured_events[0]["tool_input"]["file_path"] == "scripts/sample.py"
    assert captured_events[0]["turn_id"] == "current"


def test_privacy_post_tool_handles_run_command(monkeypatch):
    captured_events = []

    def mock_privacy_main(event):
        captured_events.append(event)
        return {}

    from scripts.hooks import privacy_gate

    monkeypatch.setattr(privacy_gate, "main", mock_privacy_main)

    payload = {
        "toolCall": {
            "name": "run_command",
            "args": {"CommandLine": "git status"},
        },
        "stepIdx": 1,
        "conversationId": "turn-bash",
    }

    result = adapter.handle_privacy_post_tool(payload)
    assert result == {}
    assert len(captured_events) == 1
    assert captured_events[0]["hook_event_name"] == "PostToolUse"
    assert captured_events[0]["tool_name"] == "Bash"
    assert captured_events[0]["turn_id"] == "turn-bash"


def test_privacy_stop_translates_block_to_continue(monkeypatch):
    from scripts.hooks import privacy_gate

    monkeypatch.setattr(
        privacy_gate,
        "main",
        lambda event: {
            "decision": "block",
            "reason": "Personal user path detected in sample.py:1",
        },
    )

    payload = {
        "executionNum": 1,
        "terminationReason": "NO_TOOL_CALL",
        "conversationId": "turn-99",
    }
    result = adapter.handle_privacy_stop(payload)
    assert result["decision"] == "continue"
    assert "Personal user path detected" in result["reason"]


def test_privacy_stop_allows_when_passing(monkeypatch):
    from scripts.hooks import privacy_gate

    monkeypatch.setattr(privacy_gate, "main", lambda event: {})

    payload = {
        "executionNum": 1,
        "terminationReason": "NO_TOOL_CALL",
        "conversationId": "turn-99",
    }
    result = adapter.handle_privacy_stop(payload)
    assert result == {}


def test_quality_stop_translates_quality_block_to_continue(monkeypatch):
    from scripts.hooks import quality_gate

    monkeypatch.setattr(
        quality_gate,
        "main",
        lambda event: {
            "decision": "block",
            "reason": "Quality checks failed: mypy error",
        },
    )

    payload = {
        "executionNum": 2,
        "terminationReason": "NO_TOOL_CALL",
        "conversationId": "turn-99",
    }
    result = adapter.handle_quality_stop(payload)
    assert result["decision"] == "continue"
    assert "Quality checks failed: mypy error" in result["reason"]


def test_quality_stop_allows_stopping_when_passing(monkeypatch):
    from scripts.hooks import quality_gate

    monkeypatch.setattr(quality_gate, "main", lambda event: {})

    payload = {
        "executionNum": 3,
        "terminationReason": "NO_TOOL_CALL",
        "conversationId": "turn-99",
    }
    result = adapter.handle_quality_stop(payload)
    assert result == {}


def test_quality_stop_allows_stopping_on_stagnated_terminal(monkeypatch):
    from scripts.hooks import quality_gate

    monkeypatch.setattr(
        quality_gate,
        "main",
        lambda event: {
            "systemMessage": "Quality repair stopped: stagnated. Unresolved failures remain."
        },
    )

    payload = {"executionNum": 4, "terminationReason": "NO_TOOL_CALL"}
    result = adapter.handle_quality_stop(payload)
    assert result == {}


def test_registered_antigravity_hooks_json_matches_codex_coverage():
    hooks_path = ROOT / ".agents/hooks.json"
    assert hooks_path.exists(), ".agents/hooks.json must exist"
    data = json.loads(hooks_path.read_text(encoding="utf-8"))

    # Both gates must be registered separately just like in Codex
    assert "quality-gate" in data
    assert "privacy-gate" in data

    q_gate = data["quality-gate"]
    assert "PostToolUse" in q_gate
    assert "Stop" in q_gate
    assert q_gate["PostToolUse"][0]["matcher"] == "edit_file|write_file"
    assert q_gate["PostToolUse"][0]["hooks"][0]["timeout"] == 600
    assert q_gate["Stop"][0]["timeout"] == 600

    p_gate = data["privacy-gate"]
    assert "PostToolUse" in p_gate
    assert "Stop" in p_gate
    # privacy-gate must match edit AND shell commands
    assert p_gate["PostToolUse"][0]["matcher"] == "edit_file|write_file|run_command"
    assert p_gate["PostToolUse"][0]["hooks"][0]["timeout"] == 60
    assert p_gate["Stop"][0]["timeout"] == 60


def test_cli_launcher_granular_actions():
    for action in (
        "quality-post-tool",
        "privacy-post-tool",
    ):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/hooks/antigravity_adapter.py"),
                action,
            ],
            cwd=ROOT,
            input=json.dumps({}),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, f"{action} failed: {result.stderr}"
        assert json.loads(result.stdout) == {}
