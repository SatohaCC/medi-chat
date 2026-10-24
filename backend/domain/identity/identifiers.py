"""Stable public identity, independent of credential providers."""

from dataclasses import dataclass

from ..foundation.primitives.identifiers import EntityUUID


@dataclass(frozen=True, slots=True)
class UserId(EntityUUID):
    """Owner identity retained when an authentication provider changes."""
