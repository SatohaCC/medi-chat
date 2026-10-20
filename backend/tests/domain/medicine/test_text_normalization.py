"""Tests for medicine name and search text normalization."""

from __future__ import annotations

import unittest

from backend.domain.shared.services import (
    normalize_match_text,
    normalize_search_text,
)


class TextNormalizationTests(unittest.TestCase):
    def test_normalize_match_text(self) -> None:
        self.assertEqual(normalize_match_text("ロキソニン Ｓ"), "ロキソニンs")
        self.assertEqual(normalize_match_text("イグザレルト（錠）"), "イグザレルト錠")

    def test_normalize_search_text(self) -> None:
        self.assertEqual(
            normalize_search_text("用法：1日1回、朝食後"), "用法 1日1回 朝食後"
        )
