"""Janome による日本語形態素解析を用いた検索キーワード抽出モジュール"""

from __future__ import annotations

from typing import Any

from janome.tokenizer import Tokenizer  # type: ignore[import-untyped]

from backend.application.retrieval.queries.models import TextSearchPolicy
from backend.infrastructure.package_insert_definitions.definition_assembly import (
    get_package_insert_definitions,
)
from backend.infrastructure.package_insert_definitions.definition_settings import (
    JanomeMorphologySettings,
)

_tokenizer: Tokenizer | None = None


def get_janome_tokenizer() -> Tokenizer:
    """形態素解析器（Tokenizer）のシングルトンインスタンスを取得する"""
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = Tokenizer()
    return _tokenizer


def extract_search_keywords(
    text: str,
    *,
    search_policy: TextSearchPolicy | None = None,
    morphology_settings: JanomeMorphologySettings | None = None,
) -> list[str]:
    """形態素解析を用いてユーザーの質問文から検索用キーワードを抽出する

    例:
        "下痢する？" -> ["下痢"]
        "頭痛は出る？" -> ["頭痛"]
        "眠くなる？" -> ["眠気", "傾眠"]
        "妊娠中に飲んでも大丈夫？" -> [] (妊娠は意図語としてJev/ロジックが担当)
        "空腹時に飲める？" -> ["空腹時", "空腹"]
        "アルコールと一緒に飲んで平気？" -> ["アルコール"]
    """
    if not text or not text.strip():
        return []

    if search_policy is None or morphology_settings is None:
        definitions = get_package_insert_definitions()
        search_policy = (
            search_policy
            if search_policy is not None
            else definitions.text_search_policy
        )
        morphology_settings = (
            morphology_settings
            if morphology_settings is not None
            else definitions.morphology_settings
        )
    search = search_policy
    stop_words = frozenset(term.value for term in search.stop_words)
    symptom_keywords = {
        rule.adjective.value: tuple(term.value for term in rule.keywords)
        for rule in search.symptom_rules
    }
    tokenizer = get_janome_tokenizer()
    tokens: list[Any] = list(tokenizer.tokenize(text))

    keywords: list[str] = []
    seen: set[str] = set()

    def add_keyword(word: str) -> None:
        clean = word.strip()
        if len(clean) >= 2 and clean not in stop_words and clean not in seen:
            seen.add(clean)
            keywords.append(clean)

    i = 0
    while i < len(tokens):
        tok = tokens[i]
        pos = tok.part_of_speech.split(",")

        # 形容詞による症状（例: 眠い -> 眠気）の検出
        if pos[0] == "形容詞":
            base = tok.base_form
            if base in symptom_keywords:
                for term in symptom_keywords[base]:
                    add_keyword(term)
            i += 1
            continue

        # 実質名詞の抽出
        if pos[0] == "名詞" and pos[1] in ("一般", "固有名詞", "サ変接続"):
            if tok.surface in stop_words:
                i += 1
                continue

            compound = tok.surface
            # 連続する名詞の先読み結合（例: 空腹 + 時 -> 空腹時、低 + 血圧 -> 低血圧）
            next_idx = i + 1
            while next_idx < len(tokens):
                next_tok = tokens[next_idx]
                next_pos = next_tok.part_of_speech.split(",")
                if next_pos[0] == "名詞" and next_pos[1] in (
                    "一般",
                    "固有名詞",
                    "サ変接続",
                    "接尾",
                ):
                    if (
                        next_tok.surface not in ("的", "等", "中")
                        and next_tok.surface
                        not in morphology_settings.ignored_noun_suffixes
                    ):
                        compound += next_tok.surface
                        next_idx += 1
                    else:
                        break
                else:
                    break

            if compound != tok.surface and compound not in stop_words:
                add_keyword(compound)
            add_keyword(tok.surface)
            i = next_idx
            continue

        i += 1

    return keywords
