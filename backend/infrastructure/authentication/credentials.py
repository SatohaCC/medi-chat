"""Bounded Argon2id verification with an unknown-account dummy hash."""

import threading

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from backend.application.authentication.errors import LoginLimited
from backend.infrastructure.persistence.postgres_authentication import (
    PostgresAuthentication,
)


class LocalCredentials:
    def __init__(self, store: PostgresAuthentication, *, parallelism: int = 2) -> None:
        self.store = store
        self.hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
        self.limit = threading.BoundedSemaphore(parallelism)
        self.dummy = self.hasher.hash("dummy password for timing only")

    def hash(self, password: str) -> str:
        if not self.limit.acquire(blocking=False):
            raise LoginLimited()
        try:
            return self.hasher.hash(password)
        finally:
            self.limit.release()

    def authenticate(self, login_id: str, password: str) -> tuple[str, int] | None:
        if not self.limit.acquire(blocking=False):
            raise LoginLimited()
        try:
            record = self.store.credential(login_id)
            valid: bool
            try:
                valid = self.hasher.verify(
                    record[1] if record else self.dummy, password
                )
            except VerificationError, InvalidHashError:
                valid = False
            return (record[0], record[3]) if record and record[2] and valid else None
        finally:
            self.limit.release()
