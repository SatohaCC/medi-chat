"""Janomeと検索語抽出契約を接続するadapter。"""

from backend.application.retrieval.queries.models import TextSearchPolicy

from .definition_settings import JanomeMorphologySettings
from .keyword_extraction import extract_search_keywords


class JanomeKeywordExtractor:
    def __init__(
        self,
        *,
        search_policy: TextSearchPolicy,
        morphology_settings: JanomeMorphologySettings,
    ) -> None:
        self._search_policy = search_policy
        self._morphology_settings = morphology_settings

    def extract_keywords(self, text: str) -> tuple[str, ...]:
        return tuple(
            extract_search_keywords(
                text,
                search_policy=self._search_policy,
                morphology_settings=self._morphology_settings,
            )
        )
