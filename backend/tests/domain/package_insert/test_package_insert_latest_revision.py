"""YJごとの採用文書は登録順ではなく原本の改訂年月で決める。"""

from dataclasses import replace

import pytest
from backend.application.package_insert_import.policies import registration_version
from backend.domain.package_insert.exceptions import PackageInsertDomainError
from backend.domain.package_insert.primitives import RevisionYearMonth
from backend.domain.package_insert.services import latest_package_insert
from backend.tests.domain.package_insert.test_package_insert_domain import _document


def version(month, digest):
    from backend.domain.package_insert.primitives import PackageInsertSha256

    document = _document()
    return registration_version(
        replace(
            document,
            source=replace(document.source, sha256=PackageInsertSha256(digest * 64)),
            revisions=(
                replace(document.revisions[0], year_month=RevisionYearMonth(month)),
            ),
        )
    )


def test_newer_revision_wins_in_both_registration_orders():
    old, new = version("2025-12", "a"), version("2026-01", "b")
    assert latest_package_insert(old, new) == new
    assert latest_package_insert(new, old) == new
    assert latest_package_insert(None, new) == new


def test_identical_original_is_idempotent():
    current = version("2026-01", "a")
    assert latest_package_insert(current, current) is current


def test_equal_revision_different_original_is_ambiguous():
    first, second = version("2026-01", "a"), version("2026-01", "b")
    with pytest.raises(PackageInsertDomainError, match="same revision"):
        latest_package_insert(first, second)
    with pytest.raises(PackageInsertDomainError, match="same revision"):
        latest_package_insert(second, first)


def test_registration_requires_revision_and_uses_latest_month_not_xml_order():
    document = _document()
    document = replace(
        document,
        source=replace(document.source, sha256=version("2026-01", "a").source_sha256),
    )
    with pytest.raises(PackageInsertDomainError, match="revision"):
        registration_version(replace(document, revisions=()))
    earlier = replace(document.revisions[0], year_month=RevisionYearMonth("2020-01"))
    later = replace(document.revisions[0], year_month=RevisionYearMonth("2026-01"))
    assert registration_version(
        replace(document, revisions=(earlier, later))
    ).revised_at == RevisionYearMonth("2026-01")
