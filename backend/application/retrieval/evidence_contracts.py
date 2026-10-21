"""根拠取得ユースケースが必要とする検索ポート。"""

from __future__ import annotations

from typing import Protocol

from backend.application.retrieval.search_models import Evidence, SearchCriteria


class EvidenceSearchTarget(Protocol):
    """根拠検索の文書と要求製品の公開識別子。"""

    @property
    def document_ids(self) -> tuple[str, ...]: ...

    @property
    def yj_codes(self) -> tuple[str, ...]: ...


class EvidenceRepository(Protocol):
    """検索条件に対応する根拠を取得するApplicationポート。"""

    async def search(
        self, criteria: SearchCriteria, medicines: tuple[EvidenceSearchTarget, ...]
    ) -> tuple[Evidence, ...]: ...
