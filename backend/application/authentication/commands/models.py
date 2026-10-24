"""Command-only results and persistence records."""

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class RefreshSession:
    user_id: str
    expires_at: int


@dataclass(frozen=True, slots=True)
class LoginResult:
    user_id: str
    expires_at: int
    refresh_expires_at: int
    access_token: str = field(repr=False)
    refresh_token: str = field(repr=False)
