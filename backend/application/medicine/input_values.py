"""外部入力を医薬品の型付き値へ変換するApplication境界。"""

from collections.abc import Sequence

from ...domain.foundation.exceptions import DomainValidationError
from ...domain.medicine.identifiers import YjCode


class InvalidMedicineInput(ValueError):
    """入力された医薬品コードが不正。HTTP等の表現は持たない。"""


def parse_yj_codes(values: Sequence[str]) -> tuple[YjCode, ...]:
    try:
        return tuple(YjCode(value) for value in values)
    except DomainValidationError:
        raise InvalidMedicineInput("Invalid product_yj_codes") from None
