"""ドメインで共有する汎用テキスト正規化処理。"""

from __future__ import annotations

import re
import unicodedata

__all__ = [
    "normalize_match_text",
    "normalize_search_text",
]


def normalize_match_text(value: str) -> str:
    """医薬品エイリアスまたは検索文字列を正規化する。"""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(char for char in normalized if char.isalnum())


def normalize_search_text(value: str) -> str:
    """全文検索比較用にテキストを正規化する。"""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.findall(r"[\w]+", normalized, flags=re.UNICODE))
