"""Real PostgreSQL contracts for identity, replay detection and atomic rotation."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from backend.application.authentication.errors import AuthenticationUnavailable
from backend.domain.identity.identifiers import UserId
from backend.infrastructure.authentication.credentials import LocalCredentials
from backend.infrastructure.authentication.tokens import RefreshSecrets
from backend.infrastructure.persistence.authentication_schema import (
    identities,
    refresh_tokens,
)
from backend.infrastructure.persistence.postgres_authentication import (
    PostgresAuthentication,
)
from backend.tests.support.postgres_fixtures import pg_engines as pg_engines
from sqlalchemy import insert, select


@pytest.fixture
def store(pg_engines):
    return PostgresAuthentication(pg_engines[1], issuer="https://test.invalid")


def provision(store):
    uid = str(UserId.generate())
    provider = LocalCredentials(store)
    store.provision(
        uid, "テスト利用者", provider.hash("test password long enough"), "local-subject"
    )
    return uid, provider


def test_real_credentials_and_stopped_account(store):
    uid, provider = provision(store)
    assert provider.authenticate("テスト利用者", "test password long enough") == (
        uid,
        0,
    )
    assert provider.authenticate("missing", "test password long enough") is None
    assert provider.authenticate("テスト利用者", "wrong password long enough") is None
    assert store.start(uid, 0, "digest", 1000, 2000)
    assert store.manage("テスト利用者")
    assert provider.authenticate("テスト利用者", "test password long enough") is None
    assert store.rotate("digest", "next", 1001) is None
    assert not store.start(uid, 0, "new", 1001, 2000)


def test_rotation_replay_revokes_entire_family(store):
    uid, _ = provision(store)
    assert store.start(uid, 0, "original", 1000, 2000)
    session = store.rotate("original", "replacement", 1001)
    assert session.user_id == uid and session.expires_at == 2000
    assert store.rotate("original", "attacker", 1002) is None
    assert store.rotate("replacement", "later", 1003) is None


def test_concurrent_rotation_has_one_winner_and_replay_revokes(store):
    uid, _ = provision(store)
    store.start(uid, 0, "original", 1000, 2000)
    barrier = Barrier(2)

    def rotate(value):
        barrier.wait(timeout=5)
        return store.rotate("original", value, 1001)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(rotate, ["next-a", "next-b"]))
    assert sum(value is not None for value in results) == 1
    assert store.rotate("next-a", "third-a", 1002) is None
    assert store.rotate("next-b", "third-b", 1002) is None


def test_partial_rotation_failure_rolls_back(store):
    uid, _ = provision(store)
    store.start(uid, 0, "original", 1000, 2000)
    store.start(uid, 0, "collision", 1000, 2000)
    with pytest.raises(AuthenticationUnavailable):
        store.rotate("original", "collision", 1001)
    assert store.rotate("original", "new", 1002) is not None


def test_password_reset_prevents_stale_login_and_revokes(store):
    uid, provider = provision(store)
    store.start(uid, 0, "old", 1000, 2000)
    store.manage(
        "テスト利用者", password_hash=provider.hash("new test password long enough")
    )
    assert provider.authenticate("テスト利用者", "test password long enough") is None
    assert provider.authenticate("テスト利用者", "new test password long enough") == (
        uid,
        1,
    )
    assert not store.start(uid, 0, "stale", 1001, 2000)
    assert store.rotate("old", "next", 1001) is None


def test_shared_rate_limit_across_instances(store, pg_engines):
    second = PostgresAuthentication(pg_engines[1], issuer="https://test.invalid")
    for index in range(10):
        assert store.admit_login("same-id", f"ip-{index}", 1000)
    assert not second.admit_login("same-id", "other-ip", 1000)
    assert second.admit_login("same-id", "other-ip", 2000)


def test_identity_mapping_and_cleanup(store, pg_engines):
    uid, _ = provision(store)
    with pg_engines[0].begin() as conn:
        conn.execute(
            insert(identities).values(
                issuer="https://new.invalid", subject="external", user_id=uid
            )
        )
    store.start(uid, 0, "expires", 1000, 1100)
    store.start(uid, 0, "retained", 1000, 2000)
    assert store.cleanup(1100) == 1
    with pg_engines[0].connect() as conn:
        assert conn.execute(select(identities.c.user_id)).scalars().all() == [uid, uid]
        assert conn.execute(select(refresh_tokens.c.digest)).scalars().all() == [
            "retained"
        ]
    assert store.rotate("retained", "next", 1100) is not None


def test_refresh_tokens_are_hashed_at_application_boundary(store):
    uid, _ = provision(store)
    secrets = RefreshSecrets()
    value = secrets.generate()
    store.start(uid, 0, secrets.digest(value), 1000, 2000)
    with store.engine.connect() as conn:
        assert value not in str(conn.execute(select(refresh_tokens)).all())
    assert store.rotate(secrets.digest(value), "next-digest", 2000) is None
