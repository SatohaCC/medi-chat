"""医薬品と添付文書参照を結ぶApplicationの読み取り投影。"""

from dataclasses import dataclass

from backend.domain.attachment.identifiers import DocumentId
from backend.domain.attachment.primitives import PmdaUrl
from backend.domain.attachment.value_objects import (
    AttachmentProductRevision,
    MedicineDocumentReference,
)
from backend.domain.medicine.entities import MedicineProduct
from backend.domain.medicine.identifiers import YjCode
from backend.domain.medicine.primitives import ProductGroupId
from backend.domain.medicine.value_objects import MedicineMatch


@dataclass(frozen=True, slots=True)
class RegisteredMedicine:
    medicine: MedicineProduct
    reference: MedicineDocumentReference

    @property
    def yj_code(self) -> YjCode | None:
        return self.medicine.yj_code

    @property
    def brand_name(self) -> str:
        return (
            self.medicine.names.brand_name.value
            if self.medicine.names.brand_name is not None
            else ""
        )

    @property
    def generic_name(self) -> str:
        return (
            self.medicine.names.generic_name.value
            if self.medicine.names.generic_name is not None
            else ""
        )

    @property
    def english_name(self) -> str:
        return (
            self.medicine.names.english_name.value
            if self.medicine.names.english_name is not None
            else ""
        )

    @property
    def hiragana_name(self) -> str:
        return (
            self.medicine.names.hiragana_name.value
            if self.medicine.names.hiragana_name is not None
            else ""
        )

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
        return (
            self.medicine.generic_name.value
            if self.medicine.generic_name is not None
            else ""
        )

    @property
    def brand_names(self) -> tuple[str, ...]:
        return tuple(value.value for value in self.medicine.brand_names)

    @property
    def yj_codes(self) -> tuple[str, ...]:
        return tuple(value.value for value in self.medicine.yj_codes)

    @property
    def matched_aliases(self) -> tuple[str, ...]:
        return tuple(value.value for value in self.medicine.matched_aliases)
