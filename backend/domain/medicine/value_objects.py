"""医薬品照合の不変な結果。"""

from dataclasses import dataclass

from .identifiers import YjCode
from .primitives import BrandName, EnglishName, GenericName, HiraganaName, MatchedAlias


@dataclass(frozen=True, slots=True, kw_only=True)
class MedicineNames:
    """製品の名称スナップショット。不在はNoneとして区別する。"""

    brand_name: BrandName | None = None
    generic_name: GenericName | None = None
    english_name: EnglishName | None = None
    hiragana_name: HiraganaName | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class MedicineMatch:
    """医薬品名称照合の結果。文書参照を含まない。"""

    generic_name: GenericName | None
    brand_names: tuple[BrandName, ...]
    yj_codes: tuple[YjCode, ...]
    matched_aliases: tuple[MatchedAlias, ...] = ()
