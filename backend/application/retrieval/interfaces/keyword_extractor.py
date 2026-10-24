"""外部技術に依存しない検索語抽出の契約。"""

from typing import Protocol


class KeywordExtractor(Protocol):
    """質問文から検索語を取り出すport。"""

    def extract_keywords(self, text: str) -> tuple[str, ...]:
        raise NotImplementedError
