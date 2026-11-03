import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.hooks.format_edited_python import edited_files
from scripts.hooks.quality_feedback import repair_state, report_feedback
from scripts.hooks.quality_gate import changed_paths, fingerprint, stop_decision


def test_repair_state_distinguishes_progress_unknown_failures_and_success():
    state = repair_state(None, 1, "A+B")
    state = repair_state(state, 1, "A")
    assert state["repeated_failures"] == 1
    state = repair_state(state, 1, "B")
    assert state["repeated_failures"] == 1
    state = repair_state(state, 0, None)
    assert state["attempts"] == 0
    assert repair_state(state, 1, "B")["repeated_failures"] == 1
    for _ in range(6):
        state = repair_state(state, 1, None)
    assert state["terminal"] == "attempt_limit"
    assert state["repeated_failures"] == 0
    assert report_feedback({"tasks": [{"status": "failed"}]})[0] is None


def test_same_diagnostic_stops_repair_even_when_source_changes(
    tmp_path, monkeypatch, stop_context
):
    from scripts.hooks import quality_gate as gate

    source = tmp_path / "changed.py"
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    monkeypatch.setattr(gate, "changed_paths", lambda root: ["changed.py"])
    calls = []

    def execute(command, **kwargs):
        calls.append(command)
        Path(command[-1]).write_text(
            json.dumps(
                {
                    "tasks": [
                        {
                            "label": "Acceptance R1",
                            "status": "failed",
                            "feedback": {
                                "identity": "same-failing-test-and-error",
                                "diagnostics": ["test_access"],
                                "suggestion": "Fix the authorization branch",
                                "docs": "docs/development/validation.md",
                            },
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=1)

    monkeypatch.setattr(gate.subprocess, "run", execute)
    event = {
        "hook_event_name": "Stop",
        "turn_id": "repair-task",
        "stop_hook_active": True,
    }
    for attempt in range(3):
        source.write_text(f"# distinct implementation {attempt}", encoding="utf-8")
        decision = gate.main(event)
        if attempt < 2:
            assert decision["decision"] == "block"
            assert "Fix the authorization branch" in decision["reason"]
        else:
            assert "decision" not in decision
            assert "stagnated" in decision["systemMessage"]
            assert "do not claim success" in decision["systemMessage"]
    assert gate.main(event)["systemMessage"]
    assert len(calls) == 3
    receipt = next(
        path
        for path in (tmp_path / ".agents/work/.hooks").glob("*.json")
        if ".report." not in path.name
    )
    state = json.loads(receipt.read_text(encoding="utf-8"))
    assert state["result"] != 0
    assert state["repeated_failures"] == 3


def test_default_task_spec_changes_invalidate_stop_success(
    tmp_path, monkeypatch, stop_context
):
    from scripts.hooks import quality_gate as gate

    monkeypatch.setattr(gate, "ROOT", tmp_path)
    monkeypatch.setattr(gate, "changed_paths", lambda root: [])
    calls = []

    def execute(*args, **kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(gate.subprocess, "run", execute)
    event = {"hook_event_name": "Stop"}
    assert gate.main(event) == {}
    spec = tmp_path / "tmp/quality/task.json"
    spec.parent.mkdir(parents=True)
    spec.write_text('{"version":1}', encoding="utf-8")
    assert gate.main(event) == {}
    assert len(calls) == 2


@pytest.fixture
def stop_context(monkeypatch):
    from scripts.hooks import quality_gate as gate

    context = ["head-and-settings-v1"]
    monkeypatch.setattr(gate, "validation_context", lambda root: context[0])
    return context


@pytest.mark.parametrize("status", ["timeout", "start_error"])
def test_runner_infrastructure_failure_is_recorded(
    tmp_path, monkeypatch, stop_context, status
):
    from scripts.hooks import quality_gate as gate

    monkeypatch.setattr(gate, "ROOT", tmp_path)
    monkeypatch.setattr(gate, "changed_paths", lambda root: [])

    directory = tmp_path / ".agents/work/.hooks"
    directory.mkdir(parents=True)
    key = gate.hashlib.sha256(b"current").hexdigest()[:24]
    (directory / f"{key}.report.json").write_text('{"status": "passed"}')

    def execute(*args, **kwargs):
        if status == "timeout":
            raise subprocess.TimeoutExpired("node", 540)
        raise FileNotFoundError("node unavailable")

    monkeypatch.setattr(gate.subprocess, "run", execute)
    assert gate.main({"hook_event_name": "Stop"})["decision"] == "block"
    receipt = json.loads(
        next((tmp_path / ".agents/work/.hooks").glob("*.json")).read_text()
    )
    assert receipt["status"] == status
    assert receipt["result"] != 0
    assert receipt["report"] is None
    assert (tmp_path / ".agents/work/.hooks" / receipt["log"]).is_file()


def test_failed_check_continues_once_but_never_claims_success():
    assert stop_decision({}, "a", None, 1)["decision"] == "block"
    previous = {"signature": "a", "result": 1}
    decision = stop_decision({"stop_hook_active": True}, "a", previous, None)
    assert "decision" not in decision
    assert "still fail" in decision["systemMessage"]
    assert stop_decision({}, "b", previous, 1)["decision"] == "block"
    assert stop_decision({}, "a", {"signature": "a", "result": 0}, None) == {}


def test_fingerprint_invalidates_changed_and_deleted_contents(tmp_path):
    file = tmp_path / "a.py"
    file.write_text("one", encoding="utf-8")
    first = fingerprint(tmp_path, ["a.py"])
    file.write_text("two", encoding="utf-8")
    second = fingerprint(tmp_path, ["a.py"])
    file.unlink()
    assert len({first, second, fingerprint(tmp_path, ["a.py"])}) == 3


def test_validation_context_tracks_head_and_clean_configuration(tmp_path):
    from scripts.hooks.quality_gate import validation_context

    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

    def commit():
        git("add", ".")
        git(
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "--no-verify",
            "--allow-empty",
            "-m",
            "fixture",
        )

    git("init")
    configuration = tmp_path / "pytest.ini"
    configuration.write_text("[pytest]\n", encoding="utf-8")
    commit()
    original = validation_context(tmp_path)
    assert validation_context(tmp_path) == original
    configuration.write_text("[pytest]\naddopts = -q\n", encoding="utf-8")
    assert validation_context(tmp_path) != original
    configuration.write_text("[pytest]\n", encoding="utf-8")
    assert validation_context(tmp_path) == original
    commit()
    assert validation_context(tmp_path) != original


def test_configuration_changes_during_validation_block_success(
    tmp_path, monkeypatch, stop_context
):
    from scripts.hooks import quality_gate as gate

    monkeypatch.setattr(gate, "ROOT", tmp_path)
    monkeypatch.setattr(gate, "changed_paths", lambda root: [])

    def execute(*args, **kwargs):
        stop_context[0] = "changed-configuration"
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(gate.subprocess, "run", execute)
    assert gate.main({"hook_event_name": "Stop"})["decision"] == "block"


def test_changed_paths_include_staged_unstaged_deleted_and_untracked(tmp_path):
    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

    git("init")
    for name in ("staged.py", "unstaged.py", "deleted.py"):
        (tmp_path / name).write_text("before", encoding="utf-8")
    git("add", ".")
    git(
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "--no-verify",
        "-m",
        "test: fixture",
    )
    (tmp_path / "staged.py").write_text("after", encoding="utf-8")
    git("add", "staged.py")
    (tmp_path / "unstaged.py").write_text("after", encoding="utf-8")
    (tmp_path / "deleted.py").unlink()
    (tmp_path / "untracked.py").write_text("new", encoding="utf-8")
    assert changed_paths(tmp_path) == [
        "deleted.py",
        "staged.py",
        "unstaged.py",
        "untracked.py",
    ]


def test_patch_string_and_structured_payloads_are_understood():
    from scripts.hooks.format_edited_python import ROOT

    file = ROOT / "scripts/hooks/quality_gate.py"
    patch = f"*** Update File: {file.as_posix()}\n"
    for payload in (patch, {"command": patch}, {"patch": patch}):
        assert edited_files({"tool_name": "apply_patch", "tool_input": payload}) == [
            file
        ]
    assert (
        edited_files(
            {"tool_name": "Write", "tool_input": {"file_path": "../outside.py"}}
        )
        == []
    )


def test_stop_runs_checks_and_reuses_only_current_success(
    tmp_path, monkeypatch, stop_context
):
    from scripts.hooks import quality_gate as gate

    source = tmp_path / "changed.py"
    source.write_text("before", encoding="utf-8")
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    monkeypatch.setattr(gate, "changed_paths", lambda root: ["changed.py"])
    calls = []

    def execute(*args, **kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(gate.subprocess, "run", execute)
    event = {"hook_event_name": "Stop", "turn_id": "test-turn"}
    assert gate.main(event) == {}
    assert gate.main(event) == {}
    assert len(calls) == 1
    source.write_text("after", encoding="utf-8")
    assert gate.main(event) == {}
    assert len(calls) == 2
    stop_context[0] = "head-and-settings-v2"
    assert gate.main(event) == {}
    assert len(calls) == 3
    receipt = next((tmp_path / ".agents/work/.hooks").glob("*.json"))
    receipt.write_text("broken json", encoding="utf-8")
    assert gate.main(event) == {}
    assert len(calls) == 4


def test_checks_cannot_certify_files_changed_during_validation(
    tmp_path, monkeypatch, stop_context
):
    from scripts.hooks import quality_gate as gate

    source = tmp_path / "changed.py"
    source.write_text("before", encoding="utf-8")
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    monkeypatch.setattr(gate, "changed_paths", lambda root: ["changed.py"])

    def execute(*args, **kwargs):
        source.write_text("changed during checks", encoding="utf-8")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(gate.subprocess, "run", execute)
    assert (
        gate.main({"hook_event_name": "Stop", "turn_id": "test-turn"})["decision"]
        == "block"
    )


def test_post_edit_formats_before_quick_checks(monkeypatch):
    from scripts.hooks import quality_gate as gate

    order = []
    monkeypatch.setattr(
        gate, "edited_paths", lambda event: [gate.ROOT / "backend/main.py"]
    )

    def format_event(event):
        order.append("format")
        return 0

    monkeypatch.setattr(gate, "format_python", format_event)

    def execute(*args, **kwargs):
        order.append("check")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(gate.subprocess, "run", execute)
    assert gate.main({"hook_event_name": "PostToolUse"}) == {}
    assert order == ["format", "check"]


def test_post_edit_returns_type_failure_and_stop_blocks(
    tmp_path, monkeypatch, stop_context
):
    from scripts.hooks import quality_gate as gate

    source = tmp_path / "backend/main.py"
    source.parent.mkdir()
    source.write_text("# test fixture", encoding="utf-8")
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    monkeypatch.setattr(gate, "edited_paths", lambda event: [source])
    monkeypatch.setattr(gate, "format_python", lambda event: 0)
    monkeypatch.setattr(gate, "changed_paths", lambda root: ["backend/main.py"])

    def execute(*args, **kwargs):
        return SimpleNamespace(
            returncode=1,
            stdout=b'main.py:1: error: Argument "database_schema" has incompatible type "str | None"; expected "str" [arg-type]',
            stderr=b"",
        )

    monkeypatch.setattr(gate.subprocess, "run", execute)
    result = gate.main({"hook_event_name": "PostToolUse"})
    assert "[arg-type]" in result["hookSpecificOutput"]["additionalContext"]
    assert gate.main({"hook_event_name": "Stop"})["decision"] == "block"


def test_project_mypy_detects_optional_schema_argument(tmp_path):
    root = Path(__file__).resolve().parents[2]
    source = tmp_path / "schema_probe.py"
    source.write_text(
        "def create_app_lifespan(*, database_schema: str) -> None:\n"
        "    pass\n"
        "def configure(schema: str | None) -> None:\n"
        "    create_app_lifespan(database_schema=schema)\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "--config-file",
            "backend/pyproject.toml",
            "--no-incremental",
            str(source),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "[arg-type]" in result.stdout
    assert '"str | None"' in result.stdout


@pytest.mark.skipif(sys.platform != "win32", reason="Windows hook launcher")
def test_registered_windows_launcher_resolves_root_from_subdirectory():
    root = Path(__file__).resolve().parents[2]
    config = json.loads((root / ".codex/hooks.json").read_text(encoding="utf-8"))
    command = config["hooks"]["PostToolUse"][0]["hooks"][0]["commandWindows"]
    result = subprocess.run(
        command,
        shell=True,
        cwd=root / "frontend",
        input=json.dumps(
            {"hook_event_name": "PostToolUse", "tool_name": "Write", "tool_input": {}}
        ),
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {}
