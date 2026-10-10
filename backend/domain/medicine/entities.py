"""医薬品コード対応表の製品情報。添付文書の情報を持たない。"""

from dataclasses import dataclass
from datetime import date

from ..medicine.identifiers import YjCode
from .primitives import (
    GenericNameCode,
    GenericPrescriptionName,
    MedicineName,
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
