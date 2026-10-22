"""添付文書自体のモデル。"""

from __future__ import annotations

from dataclasses import dataclass

from .exceptions import AttachmentDomainError
from .identifiers import DocumentId
from .value_objects import (
    AttachmentProduct,
    AttachmentReferenceTarget,
    AttachmentRevision,
    AttachmentSection,
    AttachmentSource,
    AttachmentTableBlock,
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
    reference_targets: tuple[AttachmentReferenceTarget, ...] = ()

    def __post_init__(self) -> None:
        if len({r.reference_id for r in self.reference_targets}) != len(
            self.reference_targets
        ):
            raise AttachmentDomainError(
                "an attachment cannot contain duplicate reference targets"
            )
        if len({p.product_code for p in self.products}) != len(self.products):
            raise AttachmentDomainError(
                "an attachment cannot contain duplicate products"
            )
        sections = tuple(s for root in self.sections for s in root.walk())
        section_codes = {s.code for s in sections}
        if len(section_codes) != len(sections):
            raise AttachmentDomainError(
                "an attachment cannot contain duplicate sections"
            )
        if any(s.parent_code and s.parent_code not in section_codes for s in sections):
            raise AttachmentDomainError("section parent must exist in the document")
        if any(section.parent_code is not None for section in self.sections):
            raise AttachmentDomainError("document root sections must be major sections")
        targets = {target.reference_id for target in self.reference_targets}
        for section in sections:
            if section.body is None:
                continue
            for block in section.body.blocks:
                references = list(block.references)
                if isinstance(block, AttachmentTableBlock):
                    references.extend(
                        ref
                        for row in block.table.rows
                        for cell in row
                        for ref in cell.references
                    )
                if any(
                    ref.target_id is not None and ref.target_id not in targets
                    for ref in references
                ):
                    raise AttachmentDomainError(
                        "attachment reference target is missing"
                    )
