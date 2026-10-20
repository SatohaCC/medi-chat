"""添付文書掲載製品の医薬品名称・識別子。"""

from dataclasses import dataclass

from ..medicine.identifiers import YjCode
from ..shared.services import normalize_match_text
from .primitives import ProductGroupId


@dataclass(frozen=True, slots=True)
class MedicineProduct:
    """医薬品の名称照合に使う不変情報。コード対応表・文書から独立する。"""

    yj_code: YjCode | None
    brand_name: str
    generic_name: str
    english_name: str
    hiragana_name: str

    @property
    def match_group_id(self) -> ProductGroupId | None:
        """名称照合の分類。一般名がなければ製品コードで区別する。"""
        value = normalize_match_text(self.generic_name) or (
            self.yj_code.value if self.yj_code is not None else ""
        )
        return ProductGroupId(value) if value else None
