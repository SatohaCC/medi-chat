"""Argon2 work limits and credential confidentiality."""

from unittest.mock import Mock

import pytest
from backend.application.authentication.errors import LoginLimited
from backend.infrastructure.authentication.local_credentials import LocalCredentials


def test_unknown_id_uses_dummy_hash_and_stopped_user_never_authenticates():
    store = Mock()
    provider = LocalCredentials(store, parallelism=1)
    store.credential.return_value = None
    provider.hasher = Mock(wraps=provider.hasher)
    assert provider.authenticate("missing", "unknown password long enough") is None
    provider.hasher.verify.assert_called_once_with(
        provider.dummy, "unknown password long enough"
    )
    store.credential.return_value = (
        "user",
        provider.hash("test password long enough"),
        False,
        0,
    )
    assert provider.authenticate("stopped", "test password long enough") is None


def test_busy_verification_times_out_after_loading_credentials():
    store = Mock()
    provider = LocalCredentials(store, parallelism=1)
    provider.limit = Mock()
    provider.limit.acquire.return_value = False
    provider.hasher = Mock()
    with pytest.raises(LoginLimited):
        provider.authenticate("user", "test password long enough")
    store.credential.assert_called_once_with("user")
    provider.limit.acquire.assert_called_once_with(timeout=2.0)
    provider.hasher.verify.assert_not_called()
    provider.limit.release.assert_not_called()


def test_verification_waits_for_capacity_and_db_does_not_hold_capacity():
    import threading
    from concurrent.futures import ThreadPoolExecutor

    store = Mock()
    provider = LocalCredentials(store, parallelism=1)
    entered = threading.Event()

    class ObservedSemaphore(threading.BoundedSemaphore):
        def acquire(self, *args, **kwargs):
            entered.set()
            return super().acquire(*args, **kwargs)

    provider.limit = ObservedSemaphore(1)
    assert provider.limit.acquire(blocking=False)
    entered.clear()
    store.credential.return_value = ("user", "stored-hash", True, 3)
    provider.hasher = Mock()
    provider.hasher.verify.return_value = True
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(provider.authenticate, "user", "password")
        try:
            assert entered.wait(5)
            store.credential.assert_called_once_with("user")
            provider.hasher.verify.assert_not_called()
            assert not future.done()
        finally:
            provider.limit.release()
        assert future.result(timeout=5) == ("user", 3)
    assert provider.limit.acquire(blocking=False)
    provider.limit.release()


def test_database_lookup_does_not_occupy_hash_capacity():
    store = Mock()
    provider = LocalCredentials(store, parallelism=1)

    def lookup(_):
        assert provider.limit.acquire(blocking=False)
        provider.limit.release()
        return None

    store.credential.side_effect = lookup
    provider.hasher = Mock()
    provider.hasher.verify.return_value = False
    assert provider.authenticate("missing", "password") is None


def test_unexpected_verifier_error_releases_capacity():
    store = Mock()
    store.credential.return_value = None
    provider = LocalCredentials(store, parallelism=1)
    provider.hasher = Mock()
    provider.hasher.verify.side_effect = RuntimeError("verification failed")
    with pytest.raises(RuntimeError):
        provider.authenticate("missing", "password")
    assert provider.limit.acquire(blocking=False)
    provider.limit.release()
