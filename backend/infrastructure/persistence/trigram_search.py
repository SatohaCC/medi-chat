"""Exact phrase ranking over normalized trigram projections, without SQLite.

The input is the domain's NFKC/casefold/word projection. Its Unicode codepoints
are already folded; default FTS5 trigram does not strip diacritics. Each window
contributes one token and overlapping phrase occurrences each contribute once.
BM25 uses every indexed column's token length, including nonqueried columns.
See https://www.sqlite.org/fts5.html#the_bm25_function and SQLite's fts5_aux.c.
"""

from collections.abc import Sequence
from math import log


def phrase_scores(
    texts: Sequence[str], phrase: str, *, extra_lengths: Sequence[int] = ()
) -> tuple[tuple[int, float], ...]:
    if len(phrase) < 3 or not texts:
        return ()
    lengths = [
        max(0, len(value) - 2) + (extra_lengths[index] if extra_lengths else 0)
        for index, value in enumerate(texts)
    ]
    frequencies = []
    for value in texts:
        count = 0
        start = 0
        while (start := value.find(phrase, start)) >= 0:
            count += 1
            start += 1
        frequencies.append(count)
    hit_count = sum(frequency > 0 for frequency in frequencies)
    if not hit_count:
        return ()
    inverse_frequency = log((len(texts) - hit_count + 0.5) / (hit_count + 0.5))
    if inverse_frequency <= 0:
        inverse_frequency = 1e-6
    average = sum(lengths) / len(texts)
    scores = [
        (
            index,
            -inverse_frequency
            * (
                (frequency * 2.2)
                / (frequency + 1.2 * (0.25 + 0.75 * lengths[index] / average))
            ),
        )
        for index, frequency in enumerate(frequencies)
        if frequency
    ]
    return tuple(sorted(scores, key=lambda item: (item[1], item[0])))
