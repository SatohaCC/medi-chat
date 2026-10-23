"""Application入口で単一値検証をDomainへ委譲する。"""

import pytest
from backend.application.medicine.errors import InvalidMedicineInput
from backend.application.medicine.values import parse_yj_codes
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


@pytest.mark.parametrize(
    "second", ["1234567A0000", " 1234567A0000 ", "１２３４５６７Ａ００００"]
)
def test_duplicate_normalized_codes_are_rejected(second):
    with pytest.raises(InvalidMedicineInput, match="must not contain duplicates"):
        parse_yj_codes(["1234567A0000", second])


def test_distinct_codes_preserve_input_order():
    assert parse_yj_codes(["1234567A0001", "1234567A0000"]) == (
        YjCode("1234567A0001"),
        YjCode("1234567A0000"),
    )
