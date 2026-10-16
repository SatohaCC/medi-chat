"""医薬品照合の不変な結果。"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MedicineMatch:
    """医薬品名称照合の結果。文書参照を含まない。"""

    generic_name: str
    brand_names: tuple[str, ...]
    yj_codes: tuple[str, ...]
    matched_aliases: tuple[str, ...] = ()
