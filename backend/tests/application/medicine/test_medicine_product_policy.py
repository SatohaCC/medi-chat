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
from backend.domain.medicine.primitives import (
    BrandName,
    EnglishName,
    GenericName,
    HiraganaName,
    ProductGroupId,
)
from backend.domain.medicine.value_objects import MedicineNames


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
            names=MedicineNames(
                brand_name=BrandName(name) if name else None,
                generic_name=GenericName(generic) if generic else None,
                english_name=EnglishName("Alpha tablets 10mg"),
                hiragana_name=HiraganaName("あるふぁじょう"),
            ),
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
        "names",
    }
    assert product.names.brand_name == BrandName("アルファ錠10mg")
    assert product.match_group_id == ProductGroupId("成分")


def test_same_product_preserves_multiple_document_references():
    catalog = MedicineCatalog((registered("doc-a"), registered("doc-b")))
    result = catalog.match_yj_codes((YjCode("1234567A0000"),))
    assert len(result) == 1
    assert result[0].yj_codes == ("1234567A0000",)
    assert result[0].document_ids == ("doc-a", "doc-b")
