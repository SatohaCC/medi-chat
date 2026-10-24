"""AUTH-01/05/06/07/08/10: clock-controlled authentication use cases."""

from dataclasses import dataclass
from unittest.mock import Mock

import pytest
from backend.application.authentication.commands.login import Login
from backend.application.authentication.commands.logout import Logout
from backend.application.authentication.commands.models import RefreshSession
from backend.application.authentication.commands.refresh import Refresh
from backend.application.authentication.errors import (
    AuthenticationRequired,
    LoginLimited,
)
from backend.application.authentication.queries.authenticate import Authenticate
from backend.domain.identity.identifiers import UserId


@dataclass
class Environment:
    provider: Mock
    sessions: Mock
    tokens: Mock
    secrets: Mock


@pytest.fixture
def env():
    provider, sessions, tokens, secrets = Mock(), Mock(), Mock(), Mock()
    provider.authenticate.return_value = (str(UserId.generate()), 0)
    sessions.admit_login.return_value = True
    sessions.start.return_value = True
    tokens.issue.return_value = "signed"
    secrets.generate.return_value = "random-secret"
    secrets.digest.side_effect = lambda token: "digest:" + token
    return Environment(provider, sessions, tokens, secrets)


def test_login_issues_absolute_seven_day_session(env):
    result = Login(env.provider, env.sessions, env.tokens, env.secrets).execute(
        "  Test  ", "long enough password", "127.0.0.1", 1000
    )
    assert (result.expires_at, result.refresh_expires_at) == (2800, 605800)
    env.provider.authenticate.assert_called_once_with("Test", "long enough password")
    assert "random-secret" not in repr(result)
    assert "signed" not in repr(result)


def test_login_failure_does_not_issue_tokens(env):
    env.provider.authenticate.return_value = None
    with pytest.raises(AuthenticationRequired):
        Login(env.provider, env.sessions, env.tokens, env.secrets).execute(
            "Test", "long enough password", "ip", 1000
        )
    env.sessions.start.assert_not_called()
    env.tokens.issue.assert_not_called()


def test_rate_limit_precedes_password_hash(env):
    env.sessions.admit_login.return_value = False
    with pytest.raises(LoginLimited):
        Login(env.provider, env.sessions, env.tokens, env.secrets).execute(
            "Test", "long enough password", "ip", 1000
        )
    env.provider.authenticate.assert_not_called()


def test_refresh_never_extends_absolute_expiry(env):
    env.sessions.rotate.return_value = RefreshSession("user", 1100)
    result = Refresh(env.sessions, env.tokens, env.secrets).execute("old", 1000)
    assert result.expires_at == result.refresh_expires_at == 1100
    env.sessions.rotate.assert_called_once_with(
        "digest:old", "digest:random-secret", 1000
    )


def test_refresh_rejection_does_not_issue_access(env):
    env.sessions.rotate.return_value = None
    with pytest.raises(AuthenticationRequired):
        Refresh(env.sessions, env.tokens, env.secrets).execute("old", 1000)
    env.tokens.issue.assert_not_called()


def test_logout_needs_no_valid_access_token(env):
    Logout(env.sessions, env.secrets).execute("old")
    env.sessions.revoke.assert_called_once_with("digest:old")


def test_authenticated_principal_needs_only_local_verifier():
    verifier = Mock()
    user_id = str(UserId.generate())
    verifier.verify.return_value = (user_id, 1000, 2800)
    assert Authenticate(verifier).execute("signed", 1001).user_id == user_id


def test_invalid_application_user_id_is_rejected():
    verifier = Mock()
    verifier.verify.return_value = ("not-a-user-id", 1000, 2800)
    with pytest.raises(AuthenticationRequired):
        Authenticate(verifier).execute("signed", 1001)
