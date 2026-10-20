"""医薬品Primitiveの検証と名称群・製品の値契約。"""

from dataclasses import FrozenInstanceError

import pytest
from backend.domain.foundation.exceptions import DomainValidationError
from backend.domain.medicine.entities import MedicineProduct
from backend.domain.medicine.identifiers import YjCode
from backend.domain.medicine.primitives import (
    BrandName,
    EnglishName,
    GenericName,
    HiraganaName,
    MatchedAlias,
    ProductGroupId,
)
from backend.domain.medicine.value_objects import MedicineMatch, MedicineNames


@pytest.mark.parametrize(
    "kind", [BrandName, GenericName, EnglishName, HiraganaName, MatchedAlias]
)
def test_names_preserve_original_and_are_immutable(kind):
    raw = " テスト薬１０ｍｇ（Ａ）\t"
    value = kind(raw)
    assert value.value == raw
    assert value == kind(raw)
    assert value != kind("テスト薬")
    with pytest.raises(FrozenInstanceError):
        value.value = "変更"


@pytest.mark.parametrize(
    "kind", [BrandName, GenericName, EnglishName, HiraganaName, MatchedAlias]
)
@pytest.mark.parametrize(
    "raw", ["", " \t\n　", None, 1, True, b"name", [], {}, ProductGroupId("name")]
)
def test_names_reject_empty_and_wrong_types(kind, raw):
    with pytest.raises(DomainValidationError):
        kind(raw)


def test_name_roles_are_distinct():
    assert BrandName("テスト") != GenericName("テスト")


def test_group_id_keeps_existing_normalization():
    assert ProductGroupId("　Ａ成分 ").value == "A成分"


@pytest.mark.parametrize("raw", ["", "　 ", None, 1, True])
def test_group_id_rejects_invalid_values(raw):
    with pytest.raises(DomainValidationError):
        ProductGroupId(raw)


@pytest.mark.parametrize(
    "raw",
    ["1234567A000", "1234567A00000", "1234567-0000", "あ234567A0000", None, 123, True],
)
def test_yj_rejects_invalid_values(raw):
    with pytest.raises(DomainValidationError):
        YjCode(raw)


def test_yj_normalizes_before_format_validation():
    assert YjCode("　１２３４５６７Ａ００００ ").value == "1234567A0000"
    assert YjCode("1234567a0000").value == "1234567a0000"


def test_names_allow_absence():
    assert MedicineNames() == MedicineNames()


def test_name_vo_is_immutable_and_keyword_only():
    value = MedicineNames(brand_name=BrandName("テスト"))
    assert value == MedicineNames(brand_name=BrandName("テスト"))
    with pytest.raises(FrozenInstanceError):
        value.brand_name = None  # pyright: ignore[reportAttributeAccessIssue]
    with pytest.raises(TypeError):
        MedicineNames(BrandName("テスト"))  # pyright: ignore[reportCallIssue]


def test_product_keeps_group_fallback():
    code = YjCode("1234567A0000")
    names = MedicineNames(generic_name=GenericName(" 成分Ａ "))
    assert MedicineProduct(yj_code=code, names=names).match_group_id == ProductGroupId(
        "成分a"
    )
    assert MedicineProduct(
        yj_code=code, names=MedicineNames()
    ).match_group_id == ProductGroupId(code.value)
    assert MedicineProduct(yj_code=None, names=MedicineNames()).match_group_id is None
    punctuation = MedicineNames(generic_name=GenericName("（・）"))
    assert MedicineProduct(
        yj_code=code, names=punctuation
    ).match_group_id == ProductGroupId(code.value)
    assert punctuation.generic_name == GenericName("（・）")


def test_match_keeps_order_and_is_immutable():
    first, second = BrandName("テストB"), BrandName("テストA")
    value = MedicineMatch(
        generic_name=None, brand_names=(first, second, first), yj_codes=()
    )
    assert value.brand_names == (first, second, first)
    with pytest.raises(FrozenInstanceError):
        value.brand_names = ()  # pyright: ignore[reportAttributeAccessIssue]
