"""検索語抽出の契約を用いた添付文書の検索条件生成。"""

from collections.abc import Iterable

from backend.application.retrieval.interfaces.keyword_extractor import (
    KeywordExtractor,
)
from backend.application.retrieval.queries.models import SearchCriteria
from backend.application.retrieval.values import DetectionSource, SearchKeyword


def detect_morphology_criteria(
    extractor: KeywordExtractor,
    message: str,
    excluded_terms: Iterable[str] = (),
) -> SearchCriteria | None:
    """薬剤名等を除外して質問から全文検索の条件を作る。"""
    cleaned = message
    for term in sorted(set(excluded_terms), key=len, reverse=True):
        if len(term) >= 2:
            cleaned = cleaned.replace(f"@{term}", " ")
            cleaned = cleaned.replace(f"＠{term}", " ")
            cleaned = cleaned.replace(term, " ")
    cleaned = cleaned.replace("@", " ").replace("＠", " ")

    keywords = extractor.extract_keywords(cleaned)
    if not keywords:
        return None
    return SearchCriteria(
        source=DetectionSource.KEYWORD,
        keywords=tuple(SearchKeyword(keyword) for keyword in keywords),
    )
