"""文書に登録された医薬品情報の読み取り境界。"""

from contextlib import AbstractAsyncContextManager
from typing import Protocol

from backend.application.medicine.queries.models import RegisteredMedicine
from backend.application.medicine.values import SearchGenerationId


class MedicineQueryReader(Protocol):
    async def read_medicines(self) -> tuple[RegisteredMedicine, ...]: ...


class MedicineSnapshot(Protocol):
    """同じ公開世代に属する医薬品カタログの読み取りビュー。"""

    @property
    def generation_id(self) -> SearchGenerationId: ...

    @property
    def medicine_reader(self) -> MedicineQueryReader: ...


class MedicineSnapshotProvider(Protocol):
    """カタログ取得が終わるまで公開世代を所有する境界。"""

    def acquire(self) -> AbstractAsyncContextManager[MedicineSnapshot]: ...
