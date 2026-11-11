"""Proactive 4-layer defense hooks for autonomous agent safety and loop prevention.

Layers:
1. PreInvocation: Context bloat / invocation budget veto & prompt injection detection.
2. PreToolUse: Destructive command blacklist & strict workspace directory scope guard.
3. PostToolUse / PreInvocation / Stop: Consecutive error cognitive reset & hard stop.
4. PostToolUse / Feedback Sanitization: Dynamic credential and secret redaction.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Layer 1 thresholds
WARN_INVOCATION_NUM = 50
MAX_INVOCATION_NUM = 80
MAX_INITIAL_STEPS = 250
WARN_TRANSCRIPT_BYTES = 8 * 1024 * 1024  # 8 MiB
MAX_TRANSCRIPT_BYTES = 16 * 1024 * 1024  # 16 MiB
TRANSCRIPT_TAIL_SCAN_BYTES = 64 * 1024  # 64 KiB

# Layer 3 thresholds
COGNITIVE_RESET_ERROR_THRESHOLD = 3
HARD_STOP_ERROR_THRESHOLD = 6

# Layer 1: Prompt injection patterns in untrusted external content
PROMPT_INJECTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "system_override_en",
        re.compile(
            r"(?i)\b(?:ignore|disregard|forget)\s+(?:all\s+|any\s+)?(?:previous|prior|above|system)\s+"
            r"(?:instructions|prompts|rules|directives|guidelines)\b"
        ),
    ),
    (
        "system_prompt_injection_en",
        re.compile(
            r"(?i)(?:new\s+system\s+prompt\s*:|system\s+override\s*:|"
            r"you\s+are\s+now\s+unrestricted|enter\s+developer\s+mode\s+and\s+bypass)"
        ),
    ),
    (
        "system_override_ja",
        re.compile(
            r"(?:これまでの|以前の|上記の|既存の)(?:指示|命令|ルール|システムプロンプト|制約)を"
            r"(?:すべて|全て|全部)?(?:無視|破棄|忘却|無効化)して"
        ),
    ),
)

# Layer 2: Destructive command blacklist patterns
DESTRUCTIVE_COMMAND_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "recursive_force_delete",
        re.compile(
            r"(?i)(?:\brm\s+(?:-[a-zA-Z]*r[a-zA-Z]*f|--recursive\s+--force|-[a-zA-Z]*f[a-zA-Z]*r)\s+"
            r"(?:[/\\~*]|\.\.(?:[/\\\s]|$)|\.git\b)|"
            r"\bRemove-Item\b(?=[^\r\n;|]*(?:-Recurse|-r\b))[^\r\n;|]*(?:\s\.\.(?:[/\\\s]|$)|\.git\b|[A-Za-z]:\\['\"\s]*$)|"
            r"\b(?:del|erase)\s+/s\s+/q\s+(?:[A-Za-z]:\\|\.\.)|"
            r"\b(?:rd|rmdir)\s+/s\s+/q\s+(?:[A-Za-z]:\\|\.\.|\.git\b))"
        ),
    ),
    (
        "destructive_git",
        re.compile(
            r"(?i)\bgit\s+(?:reset\s+--hard\b|clean\s+-[a-zA-Z]*f|push\s+(?:--force(?!-with-lease)|-f\b))"
        ),
    ),
    (
        "destructive_database",
        re.compile(r"(?i)\b(?:DROP\s+(?:DATABASE|SCHEMA|TABLE)\b|TRUNCATE\s+TABLE\b)"),
    ),
    (
        "dangerous_permissions",
        re.compile(
            r"(?i)(?:\bchmod\s+(?:-R\s+)?777\b|"
            r"\bicacls\b[^\r\n;|]*(?:/setintegritylevel|/grant\b[^\r\n;|]*Everyone)|"
            r"\bSet-ExecutionPolicy\s+(?:Bypass|Unrestricted)\b)"
        ),
    ),
    (
        "raw_secret_dump",
        re.compile(
            r"(?i)(?:^\s*(?:env|printenv|set)\s*$|"
            r"\bGet-ChildItem\s+Env:(?:[/\\\s'\"]|$)|"
            r"\b(?:cat|type|Get-Content|gc)\s+['\"]?(?:[\w./\\-]*[/\\])?\.env(?:\.(?!example\b|sample\b|template\b)[\w.-]+)?['\"]?(?:\s|$))"
        ),
    ),
)

# Layer 2: Sensitive file patterns blocked from direct read/write tool access
PROTECTED_FILE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)^(?:\.env|\.env\.(?!example$|sample$|template$)[\w.-]+)$"),
    re.compile(r"(?i)^id_(?:rsa|ed25519|ecdsa|dsa)(?:\.pub)?$"),
    re.compile(r"(?i)^privacy-config\.json$"),
)

# High-confidence concrete credential literals blocked at PreToolUse before entering model context
CONCRETE_CREDENTIAL_RE = re.compile(
    r"(?:\bAIzaSy[A-Za-z0-9_-]{33}\b|"
    r"\bsk-(?:proj-|ant-|live-|test-)?[A-Za-z0-9_-]{20,}\b|"
    r"\b(?:(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,})\b|"
    r"\bAKIA[0-9A-Z]{16}\b|"
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----)"
)

# Layer 4: Secret and credential redaction patterns
SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "google_api_key",
        re.compile(r"\bAIzaSy[A-Za-z0-9_-]{33}\b"),
        "[REDACTED_GOOGLE_API_KEY]",
    ),
    (
        "api_secret_key",
        re.compile(r"\bsk-(?:proj-|ant-|live-|test-)?[A-Za-z0-9_-]{20,}\b"),
        "[REDACTED_API_KEY]",
    ),
    (
        "github_token",
        re.compile(
            r"\b(?:(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,})\b"
        ),
        "[REDACTED_GITHUB_TOKEN]",
    ),
    (
        "aws_access_key",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        "[REDACTED_AWS_KEY]",
    ),
    (
        "private_key",
        re.compile(
            r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z0-9 ]*PRIVATE KEY-----"
        ),
        "[REDACTED_PRIVATE_KEY]",
    ),
    (
        "database_url_password",
        re.compile(
            r"((?:postgres(?:ql)?(?:\+\w+)?|mysql(?:\+\w+)?|redis|mongodb(?:\+srv)?)://[^:\s/@]+:)([^@\s/]+)(@)"
        ),
        r"\1[REDACTED_PASSWORD]\3",
    ),
    (
        "bearer_token",
        re.compile(r"(?i)(\bBearer\s+)[A-Za-z0-9_\-.~+/]{20,}=*"),
        r"\1[REDACTED_TOKEN]",
    ),
    (
        "generic_secret_assignment",
        re.compile(
            r"(?i)\b(api[_-]?key|secret[_-]?key|client[_-]?secret|password|passwd|access[_-]?token|auth[_-]?token)\b"
            r"(\s*[:=]\s*['\"]?)([^'\"\s,;]{8,})(['\"]?)"
        ),
        r"\1\2[REDACTED_SECRET]\4",
    ),
)


def sanitize_secrets(text: str) -> tuple[str, list[str]]:
    """Redact credentials and secrets from text before it enters agent context or logs."""
    if not text:
        return text, []
    redacted = text
    matched_kinds: list[str] = []
    for kind, pattern, replacement in SECRET_PATTERNS:
        if pattern.search(redacted):
            matched_kinds.append(kind)
            redacted = pattern.sub(replacement, redacted)
    return redacted, matched_kinds


def error_state_path(directory: Path, turn: str) -> Path:
    key = hashlib.sha256(turn.encode("utf-8")).hexdigest()[:24]
    return directory / f"{key}.proactive-errors.json"


def context_warn_path(directory: Path, turn: str) -> Path:
    key = hashlib.sha256(turn.encode("utf-8")).hexdigest()[:24]
    return directory / f"{key}.context-warned.json"


def load_error_state(directory: Path, turn: str) -> dict:
    path = error_state_path(directory, turn)
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except (OSError, ValueError):
        pass
    return {"consecutive_errors": 0, "last_error": "", "reset_injected": False}


def save_error_state(directory: Path, turn: str, state: dict) -> None:
    try:
        directory.mkdir(parents=True, exist_ok=True)
        error_state_path(directory, turn).write_text(
            json.dumps(state, ensure_ascii=False), encoding="utf-8"
        )
    except OSError:
        pass


def clear_error_state(directory: Path, turn: str) -> None:
    try:
        error_state_path(directory, turn).unlink(missing_ok=True)
    except OSError:
        pass


def record_tool_outcome(
    root: Path,
    turn: str,
    *,
    failed: bool,
    error_summary: str = "",
    step_idx: object = None,
) -> dict:
    """Record tool execution success or failure for Layer 3 loop intervention."""
    directory = root / ".agents/work/.hooks"
    state = load_error_state(directory, turn)
    same_step = step_idx is not None and state.get("last_step_idx") == step_idx

    if same_step:
        if bool(state.get("last_step_failed")):
            if failed and error_summary and not state.get("last_error"):
                sanitized_summary, _ = sanitize_secrets(error_summary[:500])
                state["last_error"] = sanitized_summary
                save_error_state(directory, turn, state)
            return state
        if not failed:
            return state
        base_count = int(state.get("prev_consecutive_errors", 0))
    else:
        base_count = int(state.get("consecutive_errors", 0))

    if not failed:
        if step_idx is None:
            clear_error_state(directory, turn)
            return {"consecutive_errors": 0, "last_error": "", "reset_injected": False}
        cleared = {
            "consecutive_errors": 0,
            "prev_consecutive_errors": base_count,
            "last_error": "",
            "reset_injected": False,
            "last_step_idx": step_idx,
            "last_step_failed": False,
        }
        save_error_state(directory, turn, cleared)
        return cleared

    count = base_count + 1
    sanitized_summary, _ = sanitize_secrets(error_summary[:500])
    updated = {
        "consecutive_errors": count,
        "prev_consecutive_errors": base_count,
        "last_error": sanitized_summary,
        "reset_injected": bool(state.get("reset_injected", False)),
        "last_step_idx": step_idx,
        "last_step_failed": True,
    }
    save_error_state(directory, turn, updated)
    return updated


def _extract_candidate_paths(tool_name: str, args: dict) -> list[str]:
    paths: list[str] = []
    for key in (
        "Path",
        "path",
        "TargetFile",
        "target_file",
        "FilePath",
        "file_path",
        "File",
        "file",
        "Directory",
        "directory",
    ):
        value = args.get(key)
        if isinstance(value, str) and value.strip():
            paths.append(value.strip())

    if tool_name in {"apply_patch"}:
        patch = args.get("command") or args.get("patch") or ""
        if isinstance(patch, str):
            for line in patch.splitlines():
                for prefix in (
                    "*** Add File: ",
                    "*** Update File: ",
                    "*** Delete File: ",
                    "*** Move to: ",
                ):
                    if line.startswith(prefix):
                        paths.append(line.removeprefix(prefix).strip())
    return paths


_INERT_HERESTRING_RE = re.compile(r"@'(?:[\s\S]*?)'@|@\"(?:[\s\S]*?)\"@")
_INERT_PROSE_FLAG_RE = re.compile(
    r"(?i)(\b(?:git\s+commit\b[^\r\n;|]*?\s(?:-m|--message)|"
    r"gh\s+(?:pr|issue|release)\s+(?:create|edit|comment)\b[^\r\n;|]*?\s(?:--body|-b|--title|-t|--notes))\s+)"
    r"(?:\"(?:\\.|[^\"\\])*\"|'(?:''|[^'])*')"
)
_SHELL_EVAL_RE = re.compile(
    r"(?i)\b(?:Invoke-Expression|iex|eval|psql|mysql|sqlite3)\b"
)


def _strip_inert_prose_arguments(cmd: str) -> str:
    """Strip non-executed prose arguments (PR bodies, commit messages, here-strings) before command blacklist scan."""
    cleaned = _INERT_PROSE_FLAG_RE.sub(r"\1\"\"", cmd)
    if not _SHELL_EVAL_RE.search(cleaned):
        cleaned = _INERT_HERESTRING_RE.sub("''", cleaned)
    return cleaned


def _is_within_allowed_roots(target: Path, allowed_roots: list[Path]) -> bool:
    resolved = target.resolve()
    return any(
        resolved == root_path or resolved.is_relative_to(root_path)
        for root_path in allowed_roots
    )


def check_pre_tool_use(payload: dict, root: Path = ROOT) -> dict:
    """Layer 2: Gate destructive commands and out-of-scope file access before execution."""
    tool_call = payload.get("toolCall", {})
    if not isinstance(tool_call, dict):
        return {"decision": "allow"}
    raw_name = str(tool_call.get("name", ""))
    tool_name = raw_name.rsplit(".", 1)[-1]
    args = tool_call.get("args", {})
    if not isinstance(args, dict):
        args = {}

    # 2.1 Check command execution tools
    if tool_name in {"run_command", "Bash", "exec_command"}:
        raw_cmd = str(
            args.get("CommandLine") or args.get("command") or args.get("cmd") or ""
        )
        cmd = _strip_inert_prose_arguments(raw_cmd)
        for rule_name, pattern in DESTRUCTIVE_COMMAND_PATTERNS:
            if pattern.search(cmd):
                return {
                    "decision": "deny",
                    "reason": (
                        f"【事前防御: 危険コマンド遮断 ({rule_name})】"
                        "破壊的操作・権限変更・または機密環境変数の直接出力を含むコマンドはブロックされました。"
                        "安全な代替手段を使用するか、ユーザーに確認してください。"
                    ),
                }

    # 2.2 Check file system scope and path traversal
    candidate_paths = _extract_candidate_paths(tool_name, args)
    if candidate_paths:
        allowed_roots = [root.resolve()]
        for ws in payload.get("workspacePaths", []) or []:
            if isinstance(ws, str) and ws.strip():
                allowed_roots.append(Path(ws).resolve())
        artifact_dir = payload.get("artifactDirectoryPath")
        if isinstance(artifact_dir, str) and artifact_dir.strip():
            allowed_roots.append(Path(artifact_dir).resolve())
        # Allow reading built-in / global Antigravity skills and brain artifacts
        home_gemini = (Path.home() / ".gemini").resolve()
        is_read_only = tool_name in {"read_file", "view_file", "Read"}
        if is_read_only:
            allowed_roots.append(home_gemini)
        else:
            allowed_roots.append((home_gemini / "antigravity" / "brain").resolve())

        for raw_path in candidate_paths:
            normalized = raw_path.replace("\\", "/")
            parts = [part for part in normalized.split("/") if part]
            if ".." in parts:
                return {
                    "decision": "deny",
                    "reason": (
                        f"【事前防御: パストラバーサル遮断】パス `{raw_path}` に `..` が含まれています。"
                        "ワークスペース内の正規パスを指定してください。"
                    ),
                }
            candidate = Path(raw_path)
            resolved = (
                candidate if candidate.is_absolute() else root / candidate
            ).resolve()
            if not _is_within_allowed_roots(resolved, allowed_roots):
                return {
                    "decision": "deny",
                    "reason": (
                        f"【事前防御: スコープ外アクセス遮断】パス `{raw_path}` は許可されたワークスペース外です。"
                    ),
                }
            basename = resolved.name
            if any(p.match(basename) for p in PROTECTED_FILE_PATTERNS):
                return {
                    "decision": "deny",
                    "reason": (
                        f"【事前防御: 機密ファイル保護】`{basename}` への直接アクセスはクレデンシャル保護のため遮断されました。"
                    ),
                }
            if ".git" in resolved.parts and not is_read_only:
                return {
                    "decision": "deny",
                    "reason": "【事前防御: Git内部ディレクトリ保護】`.git` 配下の直接変更は遮断されました。",
                }
            if is_read_only and resolved.is_file() and not resolved.is_symlink():
                try:
                    sample = resolved.read_bytes()[: 256 * 1024].decode(
                        "utf-8", errors="ignore"
                    )
                except OSError:
                    sample = ""
                if sample and CONCRETE_CREDENTIAL_RE.search(sample):
                    return {
                        "decision": "deny",
                        "reason": (
                            f"【事前防御: クレデンシャル露出遮断】`{basename}` 内に生のAPIキーまたは秘密鍵が含まれているため、"
                            "モデルコンテキストへの混入を防ぐため読み込みを遮断しました。"
                        ),
                    }

    return {"decision": "allow"}


def _scan_for_prompt_injection(text: str) -> str | None:
    if not text:
        return None
    for rule_name, pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.search(text):
            return rule_name
    return None


def _read_transcript_tail(transcript_path: Path) -> str:
    try:
        size = transcript_path.stat().st_size
        with transcript_path.open("rb") as handle:
            if size > TRANSCRIPT_TAIL_SCAN_BYTES:
                handle.seek(size - TRANSCRIPT_TAIL_SCAN_BYTES)
            raw = handle.read()
        return raw.decode("utf-8", errors="replace")
    except OSError:
        return ""


def check_pre_invocation(
    payload: dict, root: Path = ROOT, queued_messages: list[str] | None = None
) -> dict:
    """Layer 1 & Layer 3: Gate context bloat, prompt injection, and consecutive error loops."""
    turn = str(payload.get("conversationId") or "current")
    directory = root / ".agents/work/.hooks"
    directory.mkdir(parents=True, exist_ok=True)

    # 1.1 Check invocation count and step count limits
    invocation_num = payload.get("invocationNum")
    initial_steps = payload.get("initialNumSteps")
    transcript_raw = payload.get("transcriptPath")
    transcript_size = 0
    transcript_tail = ""
    if isinstance(transcript_raw, str) and transcript_raw.strip():
        tp = Path(transcript_raw)
        if tp.is_file():
            try:
                transcript_size = tp.stat().st_size
                transcript_tail = _read_transcript_tail(tp)
            except OSError:
                transcript_size = 0

    if (
        (isinstance(invocation_num, int) and invocation_num > MAX_INVOCATION_NUM)
        or (isinstance(initial_steps, int) and initial_steps > MAX_INITIAL_STEPS)
        or transcript_size > MAX_TRANSCRIPT_BYTES
    ):
        return {
            "injectSteps": [
                {
                    "errorMessage": {
                        "userMessage": (
                            "【事前防御: コンテキスト肥大化・トークン枯渇遮断】"
                            f"呼び出し回数({invocation_num})・ステップ数({initial_steps})・またはトランスクリプト容量({transcript_size} bytes)が"
                            "安全上限を超過したため、LLM呼び出しを自動遮断しました。`/compact` でコンテキストを圧縮するか新しいセッションを開始してください。"
                        )
                    }
                }
            ],
            "terminationBehavior": "terminate",
        }

    # 1.2 Check for prompt injection in queued tool feedback or recent transcript tail
    combined_external = "\n".join(queued_messages or []) + "\n" + transcript_tail
    injection_rule = _scan_for_prompt_injection(combined_external)
    if injection_rule:
        return {
            "injectSteps": [
                {
                    "errorMessage": {
                        "userMessage": (
                            f"【事前防御: プロンプトインジェクション検知 ({injection_rule})】"
                            "外部データまたはツール出力内にシステム指示を上書きする不審な命令パターンが検知されたため、"
                            "汚染されたリクエストを破棄しセッションを一時停止しました。"
                        )
                    }
                }
            ],
            "terminationBehavior": "terminate",
        }

    # 3.1 & 3.2 Check consecutive tool/check errors for Hard Stop or Cognitive Reset
    error_state = load_error_state(directory, turn)
    consecutive_errors = int(error_state.get("consecutive_errors", 0))
    if consecutive_errors >= HARD_STOP_ERROR_THRESHOLD:
        return {
            "injectSteps": [
                {
                    "errorMessage": {
                        "userMessage": (
                            f"【事前防御: 連続エラーによるハードストップ】"
                            f"思考リセット介入後もエラーが連続 {consecutive_errors} 回発生したため、"
                            "無限ループとトークン枯渇を防ぐためセッションを強制終了しました。"
                        )
                    }
                }
            ],
            "terminationBehavior": "terminate",
        }

    injected_messages: list[str] = []

    if consecutive_errors >= COGNITIVE_RESET_ERROR_THRESHOLD:
        last_err = error_state.get("last_error", "")
        injected_messages.append(
            f"【事前防御: 連続エラー検知・思考リセット介入（連続 {consecutive_errors} 回失敗）】\n"
            "同じアプローチで連続して失敗しています。直前の修正やコマンドの再実行をそのまま繰り返すのをやめてください。\n"
            "1. 失敗の根本原因（依存環境・型契約・テスト前提条件）を再確認する\n"
            "2. 別の解決策・設計アプローチへ切り替える\n"
            "3. 環境制約・権限不足が原因の場合は検査を弱めずユーザーへ報告して停止する\n"
            + (f"直近のエラー概要: {last_err}" if last_err else "")
        )
        error_state["reset_injected"] = True
        save_error_state(directory, turn, error_state)

    # Soft warning on context size / invocation count
    warn_file = context_warn_path(directory, turn)
    if (
        (isinstance(invocation_num, int) and invocation_num >= WARN_INVOCATION_NUM)
        or transcript_size >= WARN_TRANSCRIPT_BYTES
    ) and not warn_file.exists():
        try:
            warn_file.write_text(json.dumps({"warned": True}), encoding="utf-8")
        except OSError:
            pass
        injected_messages.append(
            "【事前防御: コンテキスト肥大化アラート】会話ターン数またはコンテキスト量が増加しています。"
            "不要な広範囲ファイル読込や冗長な試行を避け、現在のスコープを迅速に収束させてください。"
        )

    if not injected_messages:
        return {}
    return {"injectSteps": [{"ephemeralMessage": "\n\n".join(injected_messages)}]}
