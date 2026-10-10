"""添付文書自体のモデル。"""

from dataclasses import dataclass

from ..medicine.identifiers import YjCode
from ..shared.services import normalize_match_text
from .exceptions import AttachmentDomainError
from .identifiers import DocumentId
from .primitives import PmdaUrl, ProductGroupId
from .value_objects import (
    AttachmentProduct,
    AttachmentProductRevision,
    AttachmentRevision,
    AttachmentSection,
    AttachmentSource,
)

# 添付文書自体: 文書内の製品・項目階層の整合性を所有する


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentDocument:
    """添付文書全体の整合性を所有するAggregate Root。"""

    document_id: DocumentId
    source: AttachmentSource
    revisions: tuple[AttachmentRevision, ...] = ()
    products: tuple[AttachmentProduct, ...] = ()
    sections: tuple[AttachmentSection, ...] = ()

    def __post_init__(self) -> None:
        if len({p.product_code for p in self.products}) != len(self.products):
            raise AttachmentDomainError(
                "an attachment cannot contain duplicate products"
            )

        section_codes = {s.code for s in self.sections}
        if len(section_codes) != len(self.sections):
            raise AttachmentDomainError(
                "an attachment cannot contain duplicate sections"
            )

        if any(
            s.parent_code and s.parent_code not in section_codes for s in self.sections
        ):
            raise AttachmentDomainError("section parent must exist in the document")

    @property
    def current_revision(self) -> AttachmentRevision | None:
        """原本の並び順で先頭にある現行改訂を返す。"""
        return self.revisions[0] if self.revisions else None


@dataclass(frozen=True, slots=True)
class AttachmentProductRecord:
    """添付文書に記載された個別の医薬品製品Entity。"""

    document_id: DocumentId
    yj_code: YjCode | None
    brand_name: str
    generic_name: str
    english_name: str
    hiragana_name: str
    pmda_url: PmdaUrl
    revision: AttachmentProductRevision

    @property
    def ingredient_id(self) -> ProductGroupId:
        return ProductGroupId(
            normalize_match_text(self.generic_name)
            or (self.yj_code.value if self.yj_code is not None else "")
            or self.document_id.value
        )
