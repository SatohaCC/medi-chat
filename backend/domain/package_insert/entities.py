"""添付文書自体のモデル。"""

from __future__ import annotations

from dataclasses import dataclass

from .exceptions import PackageInsertDomainError
from .identifiers import DocumentId
from .value_objects import (
    PackageInsertProduct,
    PackageInsertReferenceTarget,
    PackageInsertRevision,
    PackageInsertSection,
    PackageInsertSource,
    PackageInsertTableBlock,
)

# 添付文書自体: 文書内の製品・項目階層の整合性を所有する


@dataclass(frozen=True, slots=True, kw_only=True)
class PackageInsertDocument:
    """添付文書全体の整合性を所有するAggregate Root。"""

    document_id: DocumentId
    source: PackageInsertSource
    revisions: tuple[PackageInsertRevision, ...] = ()
    products: tuple[PackageInsertProduct, ...] = ()
    sections: tuple[PackageInsertSection, ...] = ()
    reference_targets: tuple[PackageInsertReferenceTarget, ...] = ()

    def __post_init__(self) -> None:
        if len({r.reference_id for r in self.reference_targets}) != len(
            self.reference_targets
        ):
            raise PackageInsertDomainError(
                "an package_insert cannot contain duplicate reference targets"
            )
        if len({p.product_code for p in self.products}) != len(self.products):
            raise PackageInsertDomainError(
                "an package_insert cannot contain duplicate products"
            )
        sections = tuple(s for root in self.sections for s in root.walk())
        section_codes = {s.code for s in sections}
        if len(section_codes) != len(sections):
            raise PackageInsertDomainError(
                "an package_insert cannot contain duplicate sections"
            )
        if any(s.parent_code and s.parent_code not in section_codes for s in sections):
            raise PackageInsertDomainError("section parent must exist in the document")
        if any(section.parent_code is not None for section in self.sections):
            raise PackageInsertDomainError(
                "document root sections must be major sections"
            )
        targets = {target.reference_id for target in self.reference_targets}
        for section in sections:
            if section.body is None:
                continue
            for block in section.body.blocks:
                references = list(block.references)
                if isinstance(block, PackageInsertTableBlock):
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
                    raise PackageInsertDomainError(
                        "package_insert reference target is missing"
                    )
