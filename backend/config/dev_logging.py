"""Redact query strings from development access logs."""

import logging


class DevelopmentAccessLogFilter(logging.Filter):
    """Uvicornのアクセスログはリクエストターゲット全体を出力するため、クエリを伏せる。"""

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if isinstance(args, tuple) and len(args) == 5:
            target = args[2]
            if isinstance(target, str) and "?" in target:
                safe_args = list(args)
                safe_args[2] = f"{target.split('?', maxsplit=1)[0]}?[REDACTED]"
                record.args = tuple(safe_args)
        return True
