"""文書に登録された医薬品情報の読み取り境界。"""

from contextlib import AbstractAsyncContextManager
from typing import Protocol

from .product_models import RegisteredMedicine, SearchGenerationId


class RegisteredMedicineReader(Protocol):
    async def read_medicines(self) -> tuple[RegisteredMedicine, ...]: ...


class MedicineSnapshot(Protocol):
    """同じ公開世代に属する医薬品カタログの読み取りビュー。"""

    @property
    def generation_id(self) -> SearchGenerationId: ...

    @property
    def medicine_reader(self) -> RegisteredMedicineReader: ...


class MedicineSnapshotProvider(Protocol):
    """カタログ取得が終わるまで公開世代を所有する境界。"""

    def acquire(self) -> AbstractAsyncContextManager[MedicineSnapshot]: ...


__all__ = [
    "MedicineSnapshot",
    "MedicineSnapshotProvider",
    "RegisteredMedicineReader",
    "SearchGenerationId",
]
