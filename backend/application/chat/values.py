"""Framework-independent feedback target values."""

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

Rating = Literal["up", "down"] | None


@dataclass(frozen=True, slots=True)
class FeedbackTarget:
    run_id: UUID
    project_name: str
    user_id: str
