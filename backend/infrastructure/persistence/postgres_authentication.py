"""Shared refresh rotation and credential lifecycle with explicit row locks."""

import hashlib
import uuid
from collections.abc import Callable
from functools import wraps

from sqlalchemy import delete, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from backend.application.authentication.commands.models import RefreshSession
from backend.application.authentication.errors import AuthenticationUnavailable

from .authentication_schema import (
    attempts,
    credentials,
    families,
    identities,
    refresh_tokens,
    users,
)


def storage_operation[**P, T](operation: Callable[P, T]) -> Callable[P, T]:
    @wraps(operation)
    def protected(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return operation(*args, **kwargs)
        except SQLAlchemyError:
            raise AuthenticationUnavailable() from None

    return protected


class PostgresAuthentication:
    def __init__(
        self,
        engine: Engine,
        *,
        issuer: str,
        login_limit: int = 10,
        address_limit: int = 60,
        window_seconds: int = 900,
    ) -> None:
        self.engine, self.issuer = engine, issuer
        self.login_limit, self.address_limit, self.window_seconds = (
            login_limit,
            address_limit,
            window_seconds,
        )

    @storage_operation
    def credential(self, login_id: str) -> tuple[str, str, bool, int] | None:
        with self.engine.connect() as conn:
            row = conn.execute(
                select(
                    users.c.user_id,
                    credentials.c.password_hash,
                    users.c.active,
                    users.c.revision,
                )
                .join(credentials)
                .where(users.c.login_id == login_id)
            ).first()
            return (row[0], row[1], row[2], row[3]) if row else None

    @storage_operation
    def admit_login(self, login_id: str, address: str, now: int) -> bool:
        with self.engine.begin() as conn:
            # Deterministic lock order, including concurrent requests from the same IP.
            for name, value, limit in (
                ("address", address, self.address_limit),
                ("login", login_id, self.login_limit),
            ):
                bucket = hashlib.sha256((name + ":" + value).encode()).hexdigest()
                statement = pg_insert(attempts).values(
                    bucket=bucket, window=now // self.window_seconds, count=1
                )
                count = conn.execute(
                    statement.on_conflict_do_update(
                        index_elements=[attempts.c.bucket, attempts.c.window],
                        set_={"count": attempts.c.count + 1},
                    ).returning(attempts.c.count)
                ).scalar_one()
                if count > limit:
                    return False
        return True

    @storage_operation
    def start(
        self, user_id: str, revision: int, digest: str, now: int, expires_at: int
    ) -> bool:
        with self.engine.begin() as conn:
            user = (
                conn.execute(
                    select(users).where(users.c.user_id == user_id).with_for_update()
                )
                .mappings()
                .first()
            )
            if user is None or not user["active"] or user["revision"] != revision:
                return False
            family_id = str(uuid.uuid7())
            conn.execute(
                insert(families).values(
                    family_id=family_id,
                    user_id=user_id,
                    expires_at=expires_at,
                    revoked=False,
                )
            )
            conn.execute(
                insert(refresh_tokens).values(
                    digest=digest, family_id=family_id, used=False
                )
            )
        return True

    @storage_operation
    def rotate(self, digest: str, replacement: str, now: int) -> RefreshSession | None:
        result = None
        with self.engine.begin() as conn:
            record = conn.execute(
                select(families.c.family_id, families.c.user_id)
                .join(refresh_tokens)
                .where(refresh_tokens.c.digest == digest)
            ).first()
            if record is None:
                return None
            # Management and rotation both lock user before family to avoid inversion.
            active = conn.execute(
                select(users.c.active)
                .where(users.c.user_id == record.user_id)
                .with_for_update()
            ).scalar_one()
            family = (
                conn.execute(
                    select(families)
                    .where(families.c.family_id == record.family_id)
                    .with_for_update()
                )
                .mappings()
                .first()
            )
            if family is None:
                return None
            used = conn.execute(
                select(refresh_tokens.c.used).where(refresh_tokens.c.digest == digest)
            ).scalar_one_or_none()
            if used is None:
                return None
            if used or not active or family["expires_at"] <= now or family["revoked"]:
                conn.execute(
                    update(families)
                    .where(families.c.family_id == record.family_id)
                    .values(revoked=True)
                )
            else:
                conn.execute(
                    update(refresh_tokens)
                    .where(refresh_tokens.c.digest == digest)
                    .values(used=True)
                )
                conn.execute(
                    insert(refresh_tokens).values(
                        digest=replacement, family_id=record.family_id, used=False
                    )
                )
                result = RefreshSession(record.user_id, family["expires_at"])
        # Returning after commit preserves replay-triggered revocation.
        return result

    @storage_operation
    def revoke(self, digest: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                update(families)
                .where(
                    families.c.family_id.in_(
                        select(refresh_tokens.c.family_id).where(
                            refresh_tokens.c.digest == digest
                        )
                    )
                )
                .values(revoked=True)
            )

    @storage_operation
    def provision(
        self, user_id: str, login_id: str, password_hash: str, subject: str
    ) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                insert(users).values(
                    user_id=user_id, login_id=login_id, active=True, revision=0
                )
            )
            conn.execute(
                insert(credentials).values(user_id=user_id, password_hash=password_hash)
            )
            conn.execute(
                insert(identities).values(
                    issuer=self.issuer, subject=subject, user_id=user_id
                )
            )

    @storage_operation
    def manage(self, login_id: str, *, password_hash: str | None = None) -> bool:
        with self.engine.begin() as conn:
            user_id = conn.execute(
                select(users.c.user_id)
                .where(users.c.login_id == login_id)
                .with_for_update()
            ).scalar_one_or_none()
            if user_id is None:
                return False
            conn.execute(
                update(users)
                .where(users.c.user_id == user_id)
                .values(
                    revision=users.c.revision + 1,
                    **({"active": False} if password_hash is None else {}),
                )
            )
            if password_hash is not None:
                conn.execute(
                    update(credentials)
                    .where(credentials.c.user_id == user_id)
                    .values(password_hash=password_hash)
                )
            conn.execute(
                update(families)
                .where(families.c.user_id == user_id)
                .values(revoked=True)
            )
        return True

    @storage_operation
    def cleanup(self, now: int) -> int:
        with self.engine.begin() as conn:
            result = conn.execute(delete(families).where(families.c.expires_at <= now))
            conn.execute(
                delete(attempts).where(
                    attempts.c.window < now // self.window_seconds - 1
                )
            )
            return result.rowcount
