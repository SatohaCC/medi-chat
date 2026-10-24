"""Application user identity remains independent of a login provider."""

import pytest
from backend.domain.identity.identifiers import UserId
from backend.domain.identity.primitives import LoginId, Password


def test_user_id_and_login_normalization():
    assert UserId.parse(str(UserId.generate())).value.version == 7
    assert LoginId("  TestUser  ").value == "TestUser"
    assert LoginId("testuser") != LoginId("TestUser")


@pytest.mark.parametrize("raw", ["", "  ", "a" * 129, "a\nuser"])
def test_invalid_login_id(raw):
    with pytest.raises(ValueError):
        LoginId(raw)


@pytest.mark.parametrize("raw", ["short", "a" * 129])
def test_password_length(raw):
    with pytest.raises(ValueError):
        Password(raw)


def test_password_is_not_normalized_or_displayed():
    raw = "  sufficiently long password  "
    password = Password(raw)
    assert password.value == raw
    assert raw not in repr(password)
    assert raw not in str(password)
