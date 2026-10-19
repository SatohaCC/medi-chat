"""PG-028/029: frozen independent SQLite FTS5 results; no SQLite dependency."""

import json
import random
from pathlib import Path

import pytest
from backend.domain.shared.services import normalize_search_text
from backend.infrastructure.persistence.trigram_search import phrase_scores

ORACLE = json.loads(
    (Path(__file__).parents[2] / "fixtures/postgres_trigram_oracle.json").read_text(
        encoding="utf-8"
    )
)["cases"]


def captured_scores(texts, phrase, drug_names=()):
    matches = [
        case
        for case in ORACLE
        if case["texts"] == list(texts)
        and case["phrase"] == phrase
        and case["drug_names"] == list(drug_names)
    ]
    assert len(matches) == 1, "Oracle input is missing or ambiguous"
    return tuple(tuple(item) for item in matches[0]["expected"])


@pytest.mark.parametrize("query", ["注意事", "注意事項"])
def test_pg028_rank_and_insertion_ties_have_fixed_ids(query):
    names = ("z_tie", "best", "a_tie", "long", "metadata_only")
    texts = (
        "注意事項",
        "注意事項注意事項注意事項",
        "注意事項",
        "注意事項。" + "関係のない長い説明です。" * 10,
        "別の記載",
    )
    normalized = tuple(normalize_search_text(value) for value in texts)
    baseline = captured_scores(normalized, query)
    assert tuple(names[index] for index, _ in baseline) == (
        "best",
        "z_tie",
        "a_tie",
        "long",
    )
    actual = phrase_scores(normalized, query)
    assert tuple(index for index, _ in actual) == tuple(index for index, _ in baseline)
    assert tuple(score for _, score in actual) == pytest.approx(
        tuple(score for _, score in baseline), rel=1e-12
    )


@pytest.mark.parametrize(
    "text,query",
    [
        ("aaaaaaa", "aaaa"),
        ("ＡＢＣ１２３", "abc"),
        ("Cafe\u0301 café", "café"),
        ("café", "cafe"),
        ("漢字かな交じり文", "字かな"),
        ("カタカナｶﾀｶﾅ", "ｶﾀｶﾅ"),
        ('quoted "drug" name', '"drug"'),
        ("under_score long_word", "der_s"),
        ("東京 大阪 京都", "京 大"),
        ("𐐀𐐁𐐂𐐃", "𐐨𐐩𐐪"),
    ],
)
def test_pg029_unicode_overlap_and_phrase_boundaries_match_sqlite(text, query):
    texts = tuple(
        normalize_search_text(value)
        for value in (text, text * 3, "テスト非一致", "別の長文" * 17)
    )
    phrase = normalize_search_text(query)
    actual = phrase_scores(texts, phrase)
    expected = captured_scores(texts, phrase)
    assert tuple(index for index, _ in actual) == tuple(index for index, _ in expected)
    assert tuple(score for _, score in actual) == pytest.approx(
        tuple(score for _, score in expected), rel=1e-12
    )


def test_pg029_seeded_varied_corpora_match_independent_bm25_oracle():
    randomizer = random.Random(37051)
    alphabet = "あいう東京漢字薬abc１２éΣ_ "
    for _ in range(40):
        texts = tuple(
            normalize_search_text(
                "".join(randomizer.choices(alphabet, k=randomizer.randrange(1, 80)))
            )
            for _ in range(12)
        )
        phrase = texts[randomizer.randrange(len(texts))][: randomizer.randrange(3, 9)]
        drugs = tuple(
            normalize_search_text("薬剤名" * randomizer.randrange(0, 10)) for _ in texts
        )
        actual = phrase_scores(
            texts,
            phrase,
            extra_lengths=tuple(max(0, len(value) - 2) for value in drugs),
        )
        expected = captured_scores(texts, phrase, drugs)
        assert tuple(index for index, _ in actual) == tuple(
            index for index, _ in expected
        )
        assert tuple(score for _, score in actual) == pytest.approx(
            tuple(score for _, score in expected), rel=1e-12
        )
