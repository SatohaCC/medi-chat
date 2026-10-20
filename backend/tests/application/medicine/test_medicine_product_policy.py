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
    result = catalog.match_yj_codes(["1234567A0000"])
    assert len(result) == 1
    assert result[0].yj_codes == ("1234567A0000",)
    assert result[0].document_ids == ("doc-a", "doc-b")


def test_group_policy_keeps_highest_priority_without_breaking_ties():
    first, second = ProductGroupId("成分A"), ProductGroupId("成分B")
    assert best_alias_priorities(
        ((first, 60), (first, 90), (first, 90), (second, 85))
    ) == {first: 90, second: 85}
