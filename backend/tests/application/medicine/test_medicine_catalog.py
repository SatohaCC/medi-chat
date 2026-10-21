"""文中の薬剤名とYJコードを解決する既存の優先順位を検証する。"""

from __future__ import annotations

import pytest
from backend.application.medicine.product_catalog import MedicineCatalog, _ProductGroup
from backend.application.medicine.product_models import RegisteredMedicine
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.attachment.primitives import PmdaUrl
from backend.domain.attachment.value_objects import (
    AttachmentProductRevision,
    MedicineDocumentReference,
)
from backend.domain.medicine.entities import MedicineProduct
from backend.domain.medicine.exceptions import MedicineDomainError
from backend.domain.medicine.identifiers import YjCode
from backend.domain.medicine.primitives import (
    BrandName,
    EnglishName,
    GenericName,
    HiraganaName,
)
from backend.domain.medicine.value_objects import MedicineNames


@pytest.fixture
def registered_medicines() -> tuple[RegisteredMedicine, ...]:
    expected = tuple(
        RegisteredMedicine(
            medicine=MedicineProduct(
                yj_code=YjCode(f"1234567A000{index}"),
                names=MedicineNames(
                    brand_name=BrandName(name) if name else None,
                    generic_name=GenericName(name + "成分") if name + "成分" else None,
                    english_name=None,
                    hiragana_name=None,
                ),
            ),
            reference=MedicineDocumentReference(
                document_id=DocumentId(f"doc{index}"),
                pmda_url=PmdaUrl("https://example.test"),
                revision=AttachmentProductRevision({}),
            ),
        )
        for index, name in enumerate(["アルファ", "ベータ"])
    )
    return expected


def test_group_deduplicates_initial_and_added_products_and_aliases(
    registered_medicines,
):
    medicine = registered_medicines[0]
    products = [medicine, medicine]
    group = _ProductGroup(
        ingredient_id=medicine.ingredient_id,
        generic_name=medicine.generic_name,
        medicines=products,
    )
    products.clear()
    group.add_medicine(medicine)
    assert group.medicines == [medicine]


@pytest.mark.parametrize("on_construction", [True, False])
def test_group_rejects_other_ingredient_without_changing_products(
    registered_medicines, on_construction
):
    first, other = registered_medicines
    if on_construction:
        with pytest.raises(MedicineDomainError, match="ingredient group"):
            _ProductGroup(
                ingredient_id=first.ingredient_id,
                generic_name=first.generic_name,
                medicines=[first, other],
            )
    else:
        group = _ProductGroup(
            ingredient_id=first.ingredient_id,
            generic_name=first.generic_name,
            medicines=[first],
        )
        with pytest.raises(MedicineDomainError, match="ingredient group"):
            group.add_medicine(other)
        assert group.medicines == [first]


@pytest.mark.parametrize(
    ("codes", "expected_codes"),
    [
        (["1234567A0000"], ["1234567A0000"]),
        (["1234567A0000", "0000000A0000"], ["1234567A0000"]),
        (["0000000A0000"], []),
        (["1234567A0000", "1234567A0001"], ["1234567A0000", "1234567A0001"]),
        ([], []),
        (["1234567A0000", "1234567A0000"], ["1234567A0000"]),
    ],
)
def test_指定コードだけで対象製品を確定する(
    codes: list[str],
    expected_codes: list[str],
    registered_medicines: tuple[RegisteredMedicine, ...],
) -> None:
    groups = MedicineCatalog(registered_medicines).match_yj_codes(
        tuple(YjCode(code) for code in codes)
    )
    assert [code for group in groups for code in group.yj_codes] == expected_codes


def test_一般名aliasと薬剤全情報を保持する() -> None:
    expected = RegisteredMedicine(
        medicine=MedicineProduct(
            yj_code=YjCode("1234567A0002"),
            names=MedicineNames(
                brand_name=BrandName("商品ガンマ"),
                generic_name=GenericName("固有成分名"),
                english_name=EnglishName("DistinctCompound"),
                hiragana_name=HiraganaName("しょうひんがんま"),
            ),
        ),
        reference=MedicineDocumentReference(
            document_id=DocumentId("alias-doc"),
            pmda_url=PmdaUrl("https://example.test/original?key=1"),
            revision=AttachmentProductRevision(
                {
                    "date": "2026-09-30",
                    "source": {"label": "原文"},
                    "history": [1, None],
                }
            ),
        ),
    )
    medicines = (expected,)
    catalog = MedicineCatalog(medicines)
    groups = catalog.match_yj_codes((YjCode("1234567A0002"),))
    assert len(groups) == 1
    assert groups[0].yj_codes == ("1234567A0002",)
    assert groups[0].matched_aliases == ()
    assert "固有成分名" in catalog.names_for_yj_codes(
        tuple(YjCode(code) for code in groups[0].yj_codes)
    )
    assert groups[0].brand_names == (expected.brand_name,)
    assert groups[0].generic_name == expected.generic_name
    assert groups[0].document_ids == (expected.document_id.value,)


def test_names_for_yj_codes_includes_raw_names_and_brackets() -> None:
    expected = RegisteredMedicine(
        medicine=MedicineProduct(
            yj_code=YjCode("6179001F1025"),
            names=MedicineNames(
                brand_name=BrandName("イトラコナゾールカプセル50mg「SW」"),
                generic_name=GenericName("イトラコナゾールカプセル"),
                english_name=None,
                hiragana_name=None,
            ),
        ),
        reference=MedicineDocumentReference(
            document_id=DocumentId("doc-sw"),
            pmda_url=PmdaUrl("https://example.test/sw"),
            revision=AttachmentProductRevision({}),
        ),
    )
    medicines = (expected,)
    catalog = MedicineCatalog(medicines)
    aliases = catalog.names_for_yj_codes((YjCode("6179001F1025"),))
    assert "イトラコナゾールカプセル50mg「SW」" in aliases
    assert "SW" in aliases
