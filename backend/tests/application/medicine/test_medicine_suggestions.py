"""候補一覧の全製品保持・順序・重複排除を検証する。"""

from dataclasses import FrozenInstanceError

import pytest
from backend.application.medicine.queries.suggest_medicines import (
    MedicineSuggester,
    SuggestionProduct,
)
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.medicine.identifiers import YjCode


def product(brand, code, group="テスト成分"):
    return SuggestionProduct(
        group_name=group,
        generic_name=group,
        brand_name=brand,
        yj_code=YjCode(code),
        document_id=DocumentId("doc:" + code),
    )


def test_catalogue_preserves_all_products_and_deduplicates_references():
    alpha = product("テストアルファ", "1234567A0000")
    beta = product("テストベータ", "1234567A0001")
    gamma = product("テストガンマ", "1234567A0002", "テスト別成分")
    result = MedicineSuggester((gamma, alpha, beta, alpha)).list_all()
    assert [item.brand_names for item in result] == [
        ("テストアルファ", "テストベータ"),
        ("テストガンマ",),
    ]
    assert result[0].yj_codes == (YjCode("1234567A0000"), YjCode("1234567A0001"))
    assert result[0].document_ids == (
        DocumentId("doc:1234567A0000"),
        DocumentId("doc:1234567A0001"),
    )
    with pytest.raises(FrozenInstanceError):
        field_name = "generic_name"
        setattr(result[0], field_name, "変更")


def test_empty_catalogue():
    assert MedicineSuggester(()).list_all() == ()


def test_catalogue_projects_registered_names_without_modification():
    from backend.tests.application.medicine.test_medicine_product_policy import (
        registered,
    )

    item = registered("テスト文書", name="テスト錠10mg")
    result = MedicineSuggester.from_registered_medicines((item,)).list_all()
    assert result[0].brand_names == ("テスト錠10mg",)
    assert result[0].yj_codes == (item.yj_code,)
