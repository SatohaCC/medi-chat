"""医薬品照合の不変な結果。"""

from dataclasses import dataclass

from .exceptions import MedicineDomainError
from .identifiers import YjCode
from .primitives import BrandName, EnglishName, GenericName, HiraganaName, MatchedAlias


@dataclass(frozen=True, slots=True, kw_only=True)
class MedicineNames:
    """製品の名称スナップショット。不在はNoneとして区別する。"""

    brand_name: BrandName | None = None
    generic_name: GenericName | None = None
    english_name: EnglishName | None = None
    hiragana_name: HiraganaName | None = None

    def __post_init__(self) -> None:
        for value, kind in (
            (self.brand_name, BrandName),
            (self.generic_name, GenericName),
            (self.english_name, EnglishName),
            (self.hiragana_name, HiraganaName),
        ):
            if value is not None and not isinstance(value, kind):
                raise MedicineDomainError(f"expected {kind.__name__} or None")


@dataclass(frozen=True, slots=True, kw_only=True)
class MedicineMatch:
    """医薬品名称照合の結果。文書参照を含まない。"""

    generic_name: GenericName | None
    brand_names: tuple[BrandName, ...]
    yj_codes: tuple[YjCode, ...]
    matched_aliases: tuple[MatchedAlias, ...] = ()

    def __post_init__(self) -> None:
        if self.generic_name is not None and not isinstance(
            self.generic_name, GenericName
        ):
            raise MedicineDomainError("expected GenericName or None")
        for values, kind in (
            (self.brand_names, BrandName),
            (self.yj_codes, YjCode),
            (self.matched_aliases, MatchedAlias),
        ):
            if not isinstance(values, tuple) or any(
                not isinstance(value, kind) for value in values
            ):
                raise MedicineDomainError(f"expected tuple of {kind.__name__}")
