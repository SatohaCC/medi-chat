"""添付文書掲載製品の医薬品名称・識別子。"""

from dataclasses import dataclass

from ..medicine.identifiers import YjCode
from ..shared.services import normalize_match_text
from .exceptions import MedicineDomainError
from .primitives import ProductGroupId
from .value_objects import MedicineNames


@dataclass(frozen=True, slots=True, kw_only=True)
class MedicineProduct:
    """医薬品の名称照合に使う不変情報。コード対応表・文書から独立する。"""

    yj_code: YjCode | None
    names: MedicineNames

    def __post_init__(self) -> None:
        if self.yj_code is not None and not isinstance(self.yj_code, YjCode):
            raise MedicineDomainError("expected YjCode or None")
        if not isinstance(self.names, MedicineNames):
            raise MedicineDomainError("expected MedicineNames")

    @property
    def match_group_id(self) -> ProductGroupId | None:
        """名称照合の分類。一般名がなければ製品コードで区別する。"""
        value = normalize_match_text(
            self.names.generic_name.value if self.names.generic_name else ""
        ) or (self.yj_code.value if self.yj_code is not None else "")
        return ProductGroupId(value) if value else None
