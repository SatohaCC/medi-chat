"""ドメインで共有する汎用テキスト正規化処理。"""

from __future__ import annotations

import re
import unicodedata

__all__ = [
    "katakana_to_hiragana",
    "normalize_match_text",
    "normalize_search_text",
]


def katakana_to_hiragana(text: str) -> str:
    """カタカナをひらがなに変換する。"""
    return "".join(
        chr(ord(c) - 0x60) if 0x30A1 <= ord(c) <= 0x30F6 else c for c in text
    )


def normalize_match_text(value: str) -> str:
    """医薬品エイリアスまたは検索文字列を正規化する。"""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(char for char in normalized if char.isalnum())


def normalize_search_text(value: str) -> str:
    """全文検索比較用にテキストを正規化する。"""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.findall(r"[\w]+", normalized, flags=re.UNICODE))
