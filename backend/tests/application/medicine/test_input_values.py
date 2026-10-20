"""Application入口で単一値検証をDomainへ委譲する。"""

import pytest
from backend.application.medicine.input_values import (
    InvalidMedicineInput,
    parse_yj_codes,
)
from backend.domain.medicine.identifiers import YjCode


@pytest.mark.parametrize("code", ["short", "1234567-0000", "", "  "])
def test_invalid_codes_become_application_input_errors(code):
    with pytest.raises(InvalidMedicineInput):
        parse_yj_codes([code])


def test_normalization_and_format_are_owned_by_domain():
    assert parse_yj_codes([" １２３４５６７Ａ００００ ", "1234567a0000"]) == (
        YjCode("1234567A0000"),
        YjCode("1234567a0000"),
    )
    assert parse_yj_codes([]) == ()
