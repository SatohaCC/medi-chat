"""医薬品と添付文書参照を結ぶApplicationの読み取り投影。"""

from dataclasses import dataclass

from ...domain.attachment.identifiers import DocumentId
from ...domain.attachment.primitives import PmdaUrl
from ...domain.attachment.value_objects import (
    AttachmentProductRevision,
    MedicineDocumentReference,
)
from ...domain.medicine.entities import MedicineProduct
from ...domain.medicine.identifiers import YjCode
from ...domain.medicine.primitives import ProductGroupId
from ...domain.medicine.value_objects import MedicineMatch


@dataclass(frozen=True, slots=True)
class RegisteredMedicine:
    medicine: MedicineProduct
    reference: MedicineDocumentReference

    @property
    def yj_code(self) -> YjCode | None:
        return self.medicine.yj_code

    @property
    def brand_name(self) -> str:
        return self.medicine.brand_name

    @property
    def generic_name(self) -> str:
        return self.medicine.generic_name

    @property
    def english_name(self) -> str:
        return self.medicine.english_name

    @property
    def hiragana_name(self) -> str:
        return self.medicine.hiragana_name

    @property
    def document_id(self) -> DocumentId:
        return self.reference.document_id

    @property
    def pmda_url(self) -> PmdaUrl:
        return self.reference.pmda_url

    @property
    def revision(self) -> AttachmentProductRevision:
        return self.reference.revision

    @property
    def ingredient_id(self) -> ProductGroupId:
        # 未同定の旧入力だけは文書IDで区別する。Domainへ文書情報を渡さない。
        return self.medicine.match_group_id or ProductGroupId(self.document_id.value)


@dataclass(frozen=True, slots=True)
class ResolvedMedicine:
    medicine: MedicineMatch
    document_ids: tuple[str, ...]

    @property
    def generic_name(self) -> str:
        return self.medicine.generic_name

    @property
    def brand_names(self) -> tuple[str, ...]:
        return self.medicine.brand_names

    @property
    def yj_codes(self) -> tuple[str, ...]:
        return self.medicine.yj_codes

    @property
    def matched_aliases(self) -> tuple[str, ...]:
        return self.medicine.matched_aliases
