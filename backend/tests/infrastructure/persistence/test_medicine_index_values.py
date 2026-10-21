"""登録済みJSONから医薬品を復元する境界の型と原表記を検証する。"""

import pytest
from backend.domain.foundation.exceptions import DomainValidationError
from backend.domain.medicine.primitives import BrandName
from backend.infrastructure.index_payloads import build_index_document


def payload(product=None, generic=None):
    return {
        "document": {
            "company_identifier": "000001",
            "package_insert_no": "test",
            "generic_name": generic,
            "products": [product or {}],
        },
        "source": {"pmda_url": "https://example.test/original"},
    }


@pytest.mark.parametrize("value", [None, "", " \t　"])
def test_missing_optional_names_are_none_and_public_empty_strings(value):
    _, products = build_index_document(payload({"brand_name": value}, value))
    product = products[0]
    assert product.medicine.names.brand_name is None
    assert product.medicine.names.generic_name is None
    assert product.brand_name == product.generic_name == ""
    assert product.english_name == product.hiragana_name == ""
    assert product.ingredient_id.value == "000001_test"


@pytest.mark.parametrize(
    "field", ["brand_name", "generic_name", "english_name", "hiragana_name"]
)
@pytest.mark.parametrize("value", [False, 0, [], {}])
def test_wrong_name_types_are_not_coerced_or_treated_as_absent(field, value):
    data = payload({field: value})
    if field == "generic_name":
        data["document"][field] = value
    with pytest.raises((DomainValidationError, TypeError)):
        build_index_document(data)


def test_original_names_and_public_code_are_preserved():
    raw = " テスト錠１０ｍｇ（Ａ） "
    _, products = build_index_document(
        payload({"brand_name": raw, "yj_code": "1234567A0000"}, " テスト成分 ")
    )
    product = products[0]
    assert product.medicine.names.brand_name == BrandName(raw)
    assert product.brand_name == raw
    assert product.generic_name == " テスト成分 "
    assert product.yj_code is not None
    assert product.yj_code.value == "1234567A0000"


def test_invalid_yj_is_rejected_at_restoration():
    with pytest.raises(DomainValidationError):
        build_index_document(payload({"yj_code": "short"}))
