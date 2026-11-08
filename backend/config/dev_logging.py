"""Redact query strings from development logs."""

import logging
from typing import Any


class DevelopmentAccessLogFilter(logging.Filter):
    """UvicornのHTTPアクセスログとWebSocketハンドシェイクのクエリを伏せる。

    HTTPアクセスは ``uvicorn.access``、WebSocketのハンドシェイクは
    ``uvicorn.error`` に記録され、どちらもパスとクエリをそのまま含む。
    パス形式の引数（``/`` で始まり ``?`` を含む）だけを対象に置き換える。
    """

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if not isinstance(args, tuple):
            return True

        safe_args = None
        for index, value in enumerate(args):
            if isinstance(value, str) and value.startswith("/") and "?" in value:
                if safe_args is None:
                    safe_args = list(args)
                safe_args[index] = f"{value.split('?', maxsplit=1)[0]}?[REDACTED]"
        if safe_args is not None:
            record.args = tuple(safe_args)
        return True


# Uvicorn 0.32+のFileFilterはreload_excludesのディレクトリを相対パスのまま
# exclude_dirsに保持するため、watchfilesが報告する絶対パスと一致せず
# --reload-exclude .venv を指定しても監視から除外されない。
# 相対パスを絶対パスへ解決することで、仮想環境配下の変更による再起動を防ぐ。
try:
    import uvicorn.supervisors.watchfilesreload as _wfr

    if hasattr(_wfr, "FileFilter") and not getattr(
        _wfr.FileFilter, "_medi_chat_resolved", False
    ):
        _original_init = _wfr.FileFilter.__init__

        def _patched_file_filter_init(self: Any, config: Any) -> None:
            _original_init(self, config)
            self.exclude_dirs = [p.resolve() for p in self.exclude_dirs]

        _wfr.FileFilter.__init__ = _patched_file_filter_init  # type: ignore[assignment]
        _wfr.FileFilter._medi_chat_resolved = True  # type: ignore[attr-defined]
except ImportError:
    pass
