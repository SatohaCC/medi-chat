"""医薬品コード対応表の製品情報。添付文書の情報を持たない。"""

from dataclasses import dataclass
from datetime import date

from ..medicine.identifiers import YjCode
from ..shared.services import normalize_match_text
from .primitives import (
    GenericNameCode,
    GenericPrescriptionName,
    MedicineName,
    ProductGroupId,
    ReceiptCode,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class Medicine:
    """YJコードを識別子とする医薬品コード対応表の一製品。"""

    yj_code: YjCode
    receipt_code: ReceiptCode
    receipt_name: MedicineName
    yj_name: MedicineName
    effective_from: date
    generic_name_code: GenericNameCode | None = None
    generic_prescription_name: GenericPrescriptionName | None = None
    effective_until: date | None = None
    receipt_discontinued_on: date | None = None
    yj_discontinued_on: date | None = None


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
