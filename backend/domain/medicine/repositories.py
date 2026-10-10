"""医薬品コンテキストのRepository Interface。"""

from typing import Protocol

from .entities import Medicine


class MedicineRepository(Protocol):
    """医薬品Entityのスナップショットを取得するドメインポート。"""

    async def read_medicines(self) -> tuple[Medicine, ...]: ...
