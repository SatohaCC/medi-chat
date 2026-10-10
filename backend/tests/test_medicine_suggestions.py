"""フォーム候補の優先度・順序・入力独立性を検証する。"""

from dataclasses import FrozenInstanceError

import pytest
from backend.application.medicine.suggestions import (
    MedicineSuggester,
    SuggestionProduct,
)
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.medicine.identifiers import YjCode


def product(brand, code, group="成分", aliases=()):
    return SuggestionProduct(
        group_name=group,
        generic_name=group,
        brand_name=brand,
        yj_code=YjCode(code),
        document_id=DocumentId("doc:" + code),
        aliases=aliases,
    )


@pytest.fixture
def products():
    return (
        product("アルファ", "A", aliases=(("あるふぁ", 90), ("成分", 60))),
        product("ベータ", "B", aliases=(("べーた", 90), ("成分", 60))),
        product("ガンマ", "C", "別成分", (("がんま", 90),)),
    )


@pytest.mark.parametrize("query", [None, "", "  "])
def test_empty_query_lists_all_groups_without_duplicate_products(products, query):
    result = MedicineSuggester((*products, products[0])).suggest(query)
    assert isinstance(result, tuple)
    assert [item.brand_names for item in result] == [
        ("アルファ", "ベータ"),
        ("ガンマ",),
    ]
    assert result[0].yj_codes == (YjCode("A"), YjCode("B"))
    assert result[0].matched_aliases == ()


def test_specific_brand_has_priority_over_ingredient_alias(products):
    result = MedicineSuggester(products).suggest("成分 あるふぁ")
    assert len(result) == 1
    assert result[0].brand_names == ("アルファ",)
    assert result[0].matched_aliases == ("あるふぁ",)


def test_generic_query_includes_all_matching_products(products):
    result = MedicineSuggester(products).suggest("成分")
    assert len(result) == 1
    assert result[0].yj_codes == (YjCode("A"), YjCode("B"))
    assert result[0].matched_aliases == ("成分",)


def test_order_follows_first_mention_and_results_do_not_accumulate(products):
    suggester = MedicineSuggester(products)
    first = suggester.suggest("がんま あるふぁ あるふぁ")
    assert [item.yj_codes for item in first] == [(YjCode("C"),), (YjCode("A"),)]
    assert suggester.suggest("べーた")[0].yj_codes == (YjCode("B"),)
    assert first[1].matched_aliases == ("あるふぁ",)
    with pytest.raises(FrozenInstanceError):
        first[0].generic_name = "変更"


def test_normalization_and_unknown_query():
    suggester = MedicineSuggester((product("商品", "A", aliases=(("alpha", 90),)),))
    assert suggester.suggest(" ＡＬＰＨＡ ")[0].yj_codes == (YjCode("A"),)
    assert suggester.suggest("未登録") == ()
    assert suggester.suggest("---") == ()
