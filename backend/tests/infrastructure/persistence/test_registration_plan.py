import pytest
from backend.application.attachment_import.errors import ImportConflict
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.attachment.primitives import AttachmentSha256, RevisionYearMonth
from backend.domain.attachment.value_objects import RegistrationVersion
from backend.domain.medicine.identifiers import YjCode
from backend.infrastructure.persistence.registration_plan import plan_registration


def version(month, digest, codes=("111111111111",)):
    return RegistrationVersion(
        document_id=DocumentId("test"),
        source_sha256=AttachmentSha256(digest * 64),
        yj_codes=frozenset(YjCode(c) for c in codes),
        revised_at=RevisionYearMonth(month),
    )


def test_plan_keeps_partial_old_version_and_selects_newest_independent_of_input_order():
    old = version("2026-01", "a", ("111111111111", "222222222222"))
    newer = version("2026-03", "b")
    middle = version("2026-02", "c")
    before = dict.fromkeys(old.yj_codes, old)
    for inputs in ((middle, newer), (newer, middle)):
        plan = plan_registration(before, inputs, frozenset())
        assert dict(plan.assignments) == {
            YjCode("111111111111"): newer,
            YjCode("222222222222"): old,
        }
    assert set(before.values()) == {old}


def test_plan_does_not_reactivate_a_known_receipt():
    old = version("2026-01", "a")
    assert not plan_registration(
        {}, (old,), frozenset({old.version_id.value})
    ).assignments


def test_plan_reports_same_month_conflict():
    old, different = version("2026-01", "a"), version("2026-01", "b")
    with pytest.raises(ImportConflict):
        plan_registration({YjCode("111111111111"): old}, (different,), frozenset())
