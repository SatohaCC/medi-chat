"""Janomeと検索語抽出契約を接続するadapter。"""

from package_inserts.catalog_models import PackageInsertCatalog

from .keyword_extraction import extract_search_keywords


class JanomeKeywordExtractor:
    """注入されたカタログを用いる形態素解析adapter。"""

    def __init__(self, *, catalog: PackageInsertCatalog) -> None:
        self._catalog = catalog

    def extract_keywords(self, text: str) -> tuple[str, ...]:
        return tuple(extract_search_keywords(text, catalog=self._catalog))
