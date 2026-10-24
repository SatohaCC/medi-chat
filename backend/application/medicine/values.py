"""外部入力を医薬品の型付き値へ変換するApplication境界。"""

from collections.abc import Sequence
from dataclasses import dataclass

from backend.application.medicine.errors import InvalidMedicineInput
from backend.domain.foundation.exceptions import DomainValidationError
from backend.domain.foundation.primitives.identifiers import EntityStringId
from backend.domain.medicine.identifiers import YjCode


def parse_yj_codes(values: Sequence[str]) -> tuple[YjCode, ...]:
    try:
        codes = tuple(YjCode(value) for value in values)
    except DomainValidationError:
        raise InvalidMedicineInput("Invalid product_yj_codes") from None
    if len(codes) != len(set(codes)):
        raise InvalidMedicineInput("product_yj_codes must not contain duplicates")
    return codes


@dataclass(frozen=True, slots=True)
class SearchGenerationId(EntityStringId):
    """根拠と掲載製品を一貫して読む公開世代のID。"""
