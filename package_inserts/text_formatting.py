"""項目番号の順序と、検索単位に付けるスコープ見出しの共通処理。"""

from __future__ import annotations

from collections.abc import Sequence


def section_code_sort_key(code: str) -> tuple[int | str, ...]:
    return tuple(int(part) if part.isdigit() else part for part in code.split("."))


def format_scoped_text(text: str, scope: Sequence[str]) -> str:
    missing = [label for label in scope if label not in text]
    if not missing:
        return text
    labels = [
        label if label.startswith(("〈", "＜", "［", "[")) else f"〈{label}〉"
        for label in missing
    ]
    prefix = " ".join(labels)
    return f"{prefix}\n{text}" if "\n" in text or len(text) > 40 else f"{prefix} {text}"
