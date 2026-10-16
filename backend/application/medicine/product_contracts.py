"""文書に登録された医薬品情報の読み取り境界。"""

from typing import Protocol

from .product_models import RegisteredMedicine


class RegisteredMedicineReader(Protocol):
    async def read_medicines(self) -> tuple[RegisteredMedicine, ...]: ...
