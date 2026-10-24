"""Argon2 work limits and credential confidentiality."""

from unittest.mock import Mock

import pytest
from backend.application.authentication.errors import LoginLimited
from backend.infrastructure.authentication.credentials import LocalCredentials


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


def test_busy_hash_worker_refuses_more_work_before_loading_credentials():
    store = Mock()
    provider = LocalCredentials(store, parallelism=1)
    assert provider.limit.acquire(blocking=False)
    try:
        with pytest.raises(LoginLimited):
            provider.authenticate("user", "test password long enough")
        store.credential.assert_not_called()
    finally:
        provider.limit.release()
    assert provider.hash("test password long enough").startswith("$argon2id$")
