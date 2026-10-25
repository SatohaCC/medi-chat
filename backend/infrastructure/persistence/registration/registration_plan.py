"""Pure publication assignment planning from the state read under the DB lock."""

from collections.abc import Mapping
from dataclasses import dataclass

from backend.domain.attachment.value_objects import RegistrationVersion
from backend.domain.medicine.identifiers import YjCode
from backend.infrastructure.persistence.registration.revision_selection import (
    assign_latest,
)


@dataclass(frozen=True)
class RegistrationPlan:
    assignments: tuple[tuple[YjCode, RegistrationVersion], ...]


def plan_registration(
    active: Mapping[YjCode, RegistrationVersion],
    candidates: tuple[RegistrationVersion, ...],
    known_receipts: frozenset[str],
) -> RegistrationPlan:
    planned = dict(active)
    for version in sorted(
        candidates, key=lambda version: version.revised_at.value, reverse=True
    ):
        if version.version_id.value not in known_receipts:
            planned = assign_latest(planned, version)
    return RegistrationPlan(tuple(planned.items()))
