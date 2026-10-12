"""v5 D5: independent R5 registration oracle; no database/filesystem doubles."""

import hashlib
from dataclasses import replace
from typing import Any

import pytest
from backend.application.attachment_import.registration_contract import (
    registration_version,
)
from backend.domain.attachment.entities import AttachmentRegistration
from backend.domain.attachment.exceptions import (
    AttachmentDomainError,
    MissingOrInvalidYjError,
)
from backend.domain.attachment.identifiers import ArtifactFileId, DocumentId
from backend.domain.attachment.primitives import (
    AttachmentSha256,
    RegistrationSequence,
    RevisionYearMonth,
)
from backend.domain.attachment.value_objects import (
    ActiveRegistration,
    RegistrationVersion,
)
from backend.domain.foundation.exceptions import DomainValidationError
from backend.domain.medicine.identifiers import YjCode
from backend.domain.retrieval.entities import SearchUnit, VersionSearchSnapshot
from backend.domain.retrieval.identifiers import SearchUnitId
from backend.domain.retrieval.primitives import (
    SearchUnitKind,
    SearchUnitSectionCode,
    SearchUnitText,
)
from backend.domain.retrieval.value_objects import VersionSearchIdentity
from backend.tests.test_attachment_domain import _document

A = YjCode("3339003F5020")
B = YjCode("3961008F1020")
C = YjCode("2149044F1020")


def version(name, codes, *, document_id=None):
    original = f'<document id="{name}">fixed original {name}</document>'.encode()
    return RegistrationVersion(
        document_id=DocumentId(document_id or name),
        source_sha256=AttachmentSha256(hashlib.sha256(original).hexdigest()),
        yj_codes=frozenset(codes),
        owned_file_ids=frozenset(
            ArtifactFileId(f"{name}/{kind}")
            for kind in [
                "xml",
                "figure",
                "document",
                "units",
                "validation",
                "metadata",
                "result",
                "projection",
            ]
        ),
    )


def publish(registry, candidate):
    return registry.commit(registry.propose(candidate))


def test_tc085_unique_active_only_changes_at_commit():
    old, new, other = version("O", [A, B]), version("N", [A]), version("Q", [C])
    registry = publish(publish(AttachmentRegistration(), old), other)
    proposal = registry.propose(new)
    assert registry.sequence == 2
    assert {item.yj_code: item.version_id for item in registry.active} == {
        A: old.version_id,
        B: old.version_id,
        C: other.version_id,
    }
    updated = registry.commit(proposal)
    assert updated.sequence == 3
    assert {item.yj_code: item.version_id for item in updated.active} == {
        A: new.version_id,
        B: old.version_id,
        C: other.version_id,
    }
    assert proposal.receipt.sequence == RegistrationSequence(3)
    assert proposal.receipt.replaced_yj_codes == frozenset({A})


def test_tc086_partial_replacement_keeps_old_version_and_owned_manifest():
    old, new, other = version("O", [A, B]), version("N", [A]), version("Q", [C])
    registry = publish(publish(AttachmentRegistration(), old), other)
    updated = publish(registry, new)
    assert updated.receipts[0] is registry.receipts[0]
    assert updated.receipts[0].version is old
    assert updated.receipts[0].artifacts_deleted is False
    assert old.owned_file_ids == frozenset(
        ArtifactFileId(value)
        for value in [
            "O/xml",
            "O/figure",
            "O/document",
            "O/units",
            "O/validation",
            "O/metadata",
            "O/result",
            "O/projection",
        ]
    )
    assert {item.yj_code: item.version_id for item in updated.active} == {
        A: new.version_id,
        B: old.version_id,
        C: other.version_id,
    }


def test_tc087_only_zero_active_unleased_owned_files_are_deletable():
    old, new, final, other = (
        version("O", [A, B]),
        version("N", [A]),
        version("P", [B]),
        version("Q", [C]),
    )
    registry = publish(publish(publish(AttachmentRegistration(), old), other), new)
    assert registry.deletable_versions(frozenset()) == frozenset()
    with pytest.raises(AttachmentDomainError, match="not deletable"):
        registry.record_artifacts_deleted(old.version_id, frozenset())
    updated = publish(registry, final)
    assert updated.deletable_versions(frozenset({old.version_id})) == frozenset()
    assert updated.deletable_files(frozenset({old.version_id})) == frozenset()
    with pytest.raises(AttachmentDomainError, match="not deletable"):
        updated.record_artifacts_deleted(old.version_id, frozenset({old.version_id}))
    assert updated.deletable_versions(frozenset()) == frozenset({old.version_id})
    assert updated.deletable_files(frozenset()) == frozenset(
        ArtifactFileId(value)
        for value in [
            "O/xml",
            "O/figure",
            "O/document",
            "O/units",
            "O/validation",
            "O/metadata",
            "O/result",
            "O/projection",
        ]
    )
    assert ArtifactFileId("unowned/backup") not in updated.deletable_files(frozenset())
    assert updated.receipts[0] is registry.receipts[0]


@pytest.mark.parametrize(
    "codes", [[], [""], [None], [str(A), None], ["invalid"], [str(A), "invalid"]]
)
def test_tc088_missing_invalid_products_reject_entire_registration(codes):
    registry = publish(AttachmentRegistration(), version("Q", [C]))
    before = registry
    with pytest.raises(
        MissingOrInvalidYjError, match="missing_or_invalid_yj"
    ) as failure:
        # Empty codes/None remain missing; the explicit domain input is not repaired.
        parsed = frozenset(
            YjCode(code) if isinstance(code, str) and code else None for code in codes
        )
        invalid_input: dict[str, Any] = {
            "document_id": DocumentId("bad"),
            "source_sha256": AttachmentSha256("a" * 64),
            "yj_codes": parsed,
        }
        RegistrationVersion(**invalid_input)
    assert failure.value.code == "missing_or_invalid_yj"
    assert registry is before and registry.sequence == 1
    assert registry.receipts[0].version.document_id == DocumentId("Q")


def test_tc089_multi_yj_proposal_discard_and_commit_are_all_atomic():
    old, other, new = version("O", [A, B]), version("Q", [C]), version("N", [A, B])
    registry = publish(publish(AttachmentRegistration(), old), other)
    failed_proposal = registry.propose(new)
    assert registry.sequence == 2
    assert {item.yj_code: item.version_id for item in registry.active} == {
        A: old.version_id,
        B: old.version_id,
        C: other.version_id,
    }
    assert len(registry.receipts) == 2
    committed = registry.commit(failed_proposal)
    assert committed.sequence == 3
    assert {item.yj_code: item.version_id for item in committed.active} == {
        A: new.version_id,
        B: new.version_id,
        C: other.version_id,
    }
    assert committed.receipts[-1].replaced_yj_codes == frozenset({A, B})
    with pytest.raises(AttachmentDomainError, match="another snapshot"):
        committed.commit(failed_proposal)


@pytest.mark.parametrize("state", ["active", "partial", "superseded", "deleted"])
def test_tc090_resend_keeps_receipt_sequence_and_never_restores_old_active(state):
    old, new, final, other = (
        version("O", [A, B]),
        version("N", [A]),
        version("P", [B]),
        version("Q", [C]),
    )
    registry = publish(publish(AttachmentRegistration(), old), other)
    if state != "active":
        registry = publish(registry, new)
    if state in {"superseded", "deleted"}:
        registry = publish(registry, final)
    if state == "deleted":
        registry = registry.record_artifacts_deleted(old.version_id, frozenset())
    before = registry
    proposal = registry.propose(old)
    assert proposal.reused is True
    assert proposal.receipt is registry.receipts[0]
    assert proposal.receipt.sequence == RegistrationSequence(1)
    assert registry.commit(proposal) is before
    assert proposal.receipt.artifacts_deleted is (state == "deleted")
    expected = {
        "active": frozenset({A, B}),
        "partial": frozenset({B}),
        "superseded": frozenset(),
        "deleted": frozenset(),
    }[state]
    assert (
        frozenset(
            item.yj_code
            for item in registry.active
            if item.version_id == old.version_id
        )
        == expected
    )
    if state == "deleted":
        assert old.version_id not in registry.deletable_versions(frozenset())


def test_tc091_success_order_ignores_revision_date_and_failed_proposal():
    base = _document()
    documents = tuple(
        replace(
            base,
            source=replace(
                base.source,
                sha256=AttachmentSha256(hashlib.sha256(original).hexdigest()),
            ),
            revisions=(
                replace(base.revisions[0], year_month=RevisionYearMonth(month)),
            ),
        )
        for original, month in [
            (b"new-date", "2026-10"),
            (b"older-date", "2020-01"),
            (b"same-date-different-bytes", "2020-01"),
        ]
    )
    first, older, same_date = tuple(
        registration_version(document) for document in documents
    )
    registry = publish(AttachmentRegistration(), first)
    discarded = registry.propose(same_date)
    assert (
        registry.sequence == 1 and discarded.receipt.sequence == RegistrationSequence(2)
    )
    registry = publish(registry, older)
    assert registry.sequence == 2
    assert frozenset(item.version_id for item in registry.active) == frozenset(
        {older.version_id}
    )
    assert publish(registry, older) is registry
    registry = publish(registry, same_date)
    assert registry.sequence == 3
    assert frozenset(item.version_id for item in registry.active) == frozenset(
        {same_date.version_id}
    )
    first_revision, older_revision = (
        documents[0].current_revision,
        documents[1].current_revision,
    )
    assert first_revision is not None and older_revision is not None
    assert first_revision.year_month == RevisionYearMonth("2026-10")
    assert older_revision.year_month == RevisionYearMonth("2020-01")


def test_tc093_version_qualified_unit_ids_keep_document_identity_and_own_rows():
    old, new = (
        version("O", [A, B], document_id="same-doc"),
        version("N", [A], document_id="same-doc"),
    )
    assert old.document_id == new.document_id == DocumentId("same-doc")
    assert old.version_id != new.version_id
    old_id = VersionSearchIdentity(
        document_id=old.document_id,
        version_id=old.version_id,
        section_code=SearchUnitSectionCode("7.2"),
    )
    new_id = VersionSearchIdentity(
        document_id=new.document_id,
        version_id=new.version_id,
        section_code=SearchUnitSectionCode("7.2"),
    )
    expected_old_sha = hashlib.sha256(
        b'<document id="O">fixed original O</document>'
    ).hexdigest()
    expected_new_sha = hashlib.sha256(
        b'<document id="N">fixed original N</document>'
    ).hexdigest()
    assert old_id.unit_id == SearchUnitId(f"same-doc:{expected_old_sha}:7.2")
    assert new_id.unit_id == SearchUnitId(f"same-doc:{expected_new_sha}:7.2")
    assert old_id.unit_id != new_id.unit_id
    old_unit = SearchUnit(
        unit_id=old_id.unit_id,
        document_id=old.document_id,
        section_code=SearchUnitSectionCode("7.2"),
        kind=SearchUnitKind("section"),
        text=SearchUnitText("old original text"),
    )
    snapshot = VersionSearchSnapshot(
        document_id=old.document_id, version_id=old.version_id, units=(old_unit,)
    )
    assert snapshot.units == (old_unit,)
    assert snapshot.units[0].text == SearchUnitText("old original text")
    with pytest.raises(DomainValidationError):
        VersionSearchSnapshot(
            document_id=old.document_id, version_id=new.version_id, units=(old_unit,)
        )
    with pytest.raises(DomainValidationError):
        VersionSearchSnapshot(
            document_id=old.document_id,
            version_id=old.version_id,
            units=(old_unit, old_unit),
        )
    with pytest.raises(DomainValidationError):
        VersionSearchSnapshot(
            document_id=old.document_id,
            version_id=old.version_id,
            units=(replace(old_unit, unit_id=SearchUnitId("same-doc:7.2")),),
        )


@pytest.mark.parametrize(
    "condition",
    [
        "duplicate_active",
        "missing_active",
        "unknown_active",
        "duplicate_receipt",
        "mutable_receipts",
        "deleted_active",
    ],
)
def test_tc085_snapshot_constructor_rejects_inconsistent_or_mutable_state(condition):
    old, new = version("O", [A, B]), version("N", [A])
    registry = publish(AttachmentRegistration(), old)
    args: dict[str, Any] = {"receipts": registry.receipts, "active": registry.active}
    if condition == "duplicate_active":
        args["active"] = registry.active | frozenset(
            {ActiveRegistration(A, new.version_id)}
        )
    elif condition == "missing_active":
        args["active"] = frozenset({ActiveRegistration(A, old.version_id)})
    elif condition == "unknown_active":
        args["active"] = frozenset(
            {
                ActiveRegistration(A, new.version_id),
                ActiveRegistration(B, old.version_id),
            }
        )
    elif condition == "duplicate_receipt":
        args["receipts"] = (*registry.receipts, registry.receipts[0])
    elif condition == "mutable_receipts":
        args["receipts"] = list(registry.receipts)
    else:
        args["receipts"] = (replace(registry.receipts[0], artifacts_deleted=True),)
    with pytest.raises(AttachmentDomainError):
        AttachmentRegistration(**args)


@pytest.mark.parametrize("value", [0, -1, True])
def test_tc091_receipt_sequence_is_a_positive_integer_primitive(value):
    with pytest.raises(DomainValidationError):
        RegistrationSequence(value)


def test_tc085_forged_proposal_does_not_commit_a_different_receipt():
    old, new = version("O", [A, B]), version("N", [A])
    registry = publish(AttachmentRegistration(), old)
    proposal = registry.propose(new)
    with pytest.raises(AttachmentDomainError):
        registry.commit(replace(proposal, receipt=registry.receipts[0]))
