"""検索条件に対応する根拠の取得ポート。"""

from typing import Protocol

from .value_objects import Evidence, SearchCriteria


class EvidenceSearchTarget(Protocol):
    """根拠検索に必要な文書IDだけを公開する入力契約。"""

    @property
    def document_ids(self) -> tuple[str, ...]: ...


class EvidenceRepository(Protocol):
    """検索条件に対応する根拠を取得するドメインポート。"""

    async def search(
        self, criteria: SearchCriteria, medicines: tuple[EvidenceSearchTarget, ...]
    ) -> tuple[Evidence, ...]: ...
