"""添付文書自体のモデル。"""

from dataclasses import dataclass, replace

from ..medicine.identifiers import YjCode
from ..shared.services import normalize_match_text
from .exceptions import AttachmentDomainError
from .identifiers import ArtifactFileId, DocumentId, DocumentVersionId
from .primitives import PmdaUrl, ProductGroupId, RegistrationSequence
from .value_objects import (
    ActiveRegistration,
    AttachmentProduct,
    AttachmentProductRevision,
    AttachmentReferenceTarget,
    AttachmentRevision,
    AttachmentSection,
    AttachmentSource,
    RegistrationProposal,
    RegistrationReceipt,
    RegistrationVersion,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentRegistration:
    receipts: tuple[RegistrationReceipt, ...] = ()
    active: frozenset[ActiveRegistration] = frozenset()

    def __post_init__(self) -> None:
        if not isinstance(self.receipts, tuple) or not isinstance(
            self.active, frozenset
        ):
            raise AttachmentDomainError(
                "registration snapshot collections must be immutable"
            )
        if len({receipt.version.version_id for receipt in self.receipts}) != len(
            self.receipts
        ):
            raise AttachmentDomainError(
                "one first-success receipt per original version"
            )
        if tuple(receipt.sequence.value for receipt in self.receipts) != tuple(
            range(1, len(self.receipts) + 1)
        ):
            raise AttachmentDomainError(
                "receipts must retain contiguous first-success order"
            )
        expected = {}
        for receipt in self.receipts:
            if receipt.replaced_yj_codes != frozenset(
                code for code in receipt.version.yj_codes if code in expected
            ):
                raise AttachmentDomainError(
                    "receipt replacement metadata must retain first-success assignments"
                )
            for code in receipt.version.yj_codes:
                expected[code] = receipt.version.version_id
        expected_active = frozenset(
            ActiveRegistration(code, version_id)
            for code, version_id in expected.items()
        )
        if self.active != expected_active:
            raise AttachmentDomainError(
                "active assignments must match unique successful registration order"
            )
        active_versions = frozenset(item.version_id for item in self.active)
        if any(
            receipt.artifacts_deleted and receipt.version.version_id in active_versions
            for receipt in self.receipts
        ):
            raise AttachmentDomainError("active version artifacts cannot be deleted")

    @property
    def sequence(self) -> int:
        return len(self.receipts)

    def propose(self, version: RegistrationVersion) -> RegistrationProposal:
        existing = next(
            (
                receipt
                for receipt in self.receipts
                if receipt.version.version_id == version.version_id
            ),
            None,
        )
        if existing is not None:
            return RegistrationProposal(
                before=self, after=self, receipt=existing, reused=True
            )
        replaced = frozenset(
            item.yj_code for item in self.active if item.yj_code in version.yj_codes
        )
        receipt = RegistrationReceipt(
            version=version,
            sequence=RegistrationSequence(self.sequence + 1),
            replaced_yj_codes=replaced,
        )
        active = frozenset(
            item for item in self.active if item.yj_code not in version.yj_codes
        ) | frozenset(
            ActiveRegistration(code, version.version_id) for code in version.yj_codes
        )
        after = AttachmentRegistration(
            receipts=(*self.receipts, receipt), active=active
        )
        return RegistrationProposal(
            before=self, after=after, receipt=receipt, reused=False
        )

    def commit(self, proposal: RegistrationProposal) -> AttachmentRegistration:
        if proposal.before != self:
            raise AttachmentDomainError(
                "registration proposal was prepared against another snapshot"
            )
        if proposal != self.propose(proposal.receipt.version):
            raise AttachmentDomainError(
                "registration proposal does not match its receipt and next snapshot"
            )
        return proposal.after

    def deletable_versions(
        self, leased_version_ids: frozenset[DocumentVersionId]
    ) -> frozenset[DocumentVersionId]:
        protected = (
            frozenset(item.version_id for item in self.active) | leased_version_ids
        )
        return frozenset(
            receipt.version.version_id
            for receipt in self.receipts
            if receipt.version.version_id not in protected
            and not receipt.artifacts_deleted
        )

    def deletable_files(
        self, leased_version_ids: frozenset[DocumentVersionId]
    ) -> frozenset[ArtifactFileId]:
        eligible = self.deletable_versions(leased_version_ids)
        removable = frozenset(
            file_id
            for receipt in self.receipts
            if receipt.version.version_id in eligible
            for file_id in receipt.version.owned_file_ids
        )
        protected = frozenset(
            file_id
            for receipt in self.receipts
            if receipt.version.version_id not in eligible
            and not receipt.artifacts_deleted
            for file_id in receipt.version.owned_file_ids
        )
        return removable - protected

    def record_artifacts_deleted(
        self,
        version_id: DocumentVersionId,
        leased_version_ids: frozenset[DocumentVersionId],
    ) -> AttachmentRegistration:
        if version_id not in self.deletable_versions(leased_version_ids):
            raise AttachmentDomainError(
                "active, leased, unknown or already deleted version is not deletable"
            )
        receipts = tuple(
            replace(receipt, artifacts_deleted=True)
            if receipt.version.version_id == version_id
            else receipt
            for receipt in self.receipts
        )
        return AttachmentRegistration(receipts=receipts, active=self.active)


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
