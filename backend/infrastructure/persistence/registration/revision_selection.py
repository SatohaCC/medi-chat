"""登録する原本の改訂年月に基づく公開先選択。"""

from backend.application.package_insert_import.errors import ImportConflict
from backend.domain.medicine.identifiers import YjCode
from backend.domain.package_insert.exceptions import ConflictingRevisionError
from backend.domain.package_insert.services import latest_package_insert
from backend.domain.package_insert.value_objects import RegistrationVersion


def assign_latest(
    active: dict[YjCode, RegistrationVersion], version: RegistrationVersion
) -> dict[YjCode, RegistrationVersion]:
    updated = dict(active)
    for code in sorted(version.yj_codes, key=lambda code: code.value):
        try:
            updated[code] = latest_package_insert(active.get(code), version)
        except ConflictingRevisionError as exc:
            error = ImportConflict(
                "same_revision_conflict",
                "Different originals for the same YJ code have the same revision month",
                phase="validation",
            )
            error.conflicts = (
                (
                    code.value,
                    tuple(
                        sorted(
                            {active[code].version_id.value, version.version_id.value}
                        )
                    ),
                ),
            )
            raise error from exc
    return updated
