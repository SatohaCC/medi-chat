"""医薬品の照合規則と文書対応の分離を、実モデルで検証する。"""

from dataclasses import fields

from backend.application.medicine.product_catalog import MedicineCatalog
from backend.application.medicine.product_models import RegisteredMedicine
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.attachment.primitives import PmdaUrl
from backend.domain.attachment.value_objects import (
    AttachmentProductRevision,
    MedicineDocumentReference,
)
from backend.domain.medicine.entities import MedicineProduct
from backend.domain.medicine.identifiers import YjCode
from backend.domain.medicine.primitives import ProductGroupId
from backend.domain.medicine.services import best_alias_priorities, get_weighted_aliases


def registered(
    document_id: str,
    *,
    code: str | None = "1234567A0000",
    name: str = "アルファ錠10mg",
    generic: str = "成分",
) -> RegisteredMedicine:
    return RegisteredMedicine(
        medicine=MedicineProduct(
            yj_code=YjCode(code) if code else None,
            brand_name=name,
            generic_name=generic,
            english_name="Alpha tablets 10mg",
            hiragana_name="あるふぁじょう",
        ),
        reference=MedicineDocumentReference(
            document_id=DocumentId(document_id),
            pmda_url=PmdaUrl("https://example.test/original"),
            revision=AttachmentProductRevision({"unknown": [1, None]}),
        ),
    )


def test_medicine_policy_needs_no_document_or_code_table():
    product = registered("doc").medicine
    assert {f.name for f in fields(product)} == {
        "yj_code",
        "brand_name",
        "generic_name",
        "english_name",
        "hiragana_name",
    }
    aliases = dict(get_weighted_aliases(product))
    assert aliases["1234567a0000"] == 100
    assert aliases["アルファ錠10mg"] == 90
    assert aliases["アルファ"] == 85
    assert product.brand_name == "アルファ錠10mg"
    assert product.match_group_id == ProductGroupId("成分")


def test_same_product_preserves_multiple_document_references():
    catalog = MedicineCatalog((registered("doc-a"), registered("doc-b")))
    result = catalog.resolve_medicines("別の名称", ["1234567A0000"])
    assert len(result) == 1
    assert result[0].yj_codes == ("1234567A0000",)
    assert result[0].document_ids == ("doc-a", "doc-b")
    assert catalog.question_name_candidates("アルファ") == frozenset(
        {YjCode("1234567A0000")}
    )
    assert catalog.question_name_candidates("アルファについて") == frozenset()


def test_legacy_unidentified_products_keep_document_fallback():
    first = registered("doc-a", code=None, generic="")
    second = registered("doc-b", code=None, generic="")
    assert first.medicine.match_group_id is None
    result = MedicineCatalog((first, second)).match_text("アルファ")
    assert [item.document_ids for item in result] == [("doc-a",), ("doc-b",)]
    assert all(item.yj_codes == () for item in result)


def test_group_policy_keeps_highest_priority_without_breaking_ties():
    first, second = ProductGroupId("成分A"), ProductGroupId("成分B")
    assert best_alias_priorities(
        ((first, 60), (first, 90), (first, 90), (second, 85))
    ) == {first: 90, second: 85}


def test_matching_keeps_first_mention_order_and_equal_priority_products():
    products = (
        registered("a", name="アルファ錠10mg", generic="成分A"),
        registered("a2", code="1234567A0001", name="アルファ錠20mg", generic="成分A"),
        registered("b", code="1234567A0002", name="ベータ錠10mg", generic="成分B"),
    )
    result = MedicineCatalog(products).match_text("ベータとアルファの副作用")
    assert [item.generic_name for item in result] == ["成分B", "成分A"]
    assert result[1].yj_codes == ("1234567A0000", "1234567A0001")
