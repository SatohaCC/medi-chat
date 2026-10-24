"""Composition of local credentials, use cases and required keys."""

from types import SimpleNamespace

from sqlalchemy.engine import Engine

from backend.application.authentication.commands.login import Login
from backend.application.authentication.commands.logout import Logout
from backend.application.authentication.commands.refresh import Refresh
from backend.application.authentication.queries.authenticate import Authenticate
from backend.config.authentication_settings import read_authentication_settings
from backend.infrastructure.authentication.credentials import LocalCredentials
from backend.infrastructure.authentication.tokens import JwtTokens, RefreshSecrets
from backend.infrastructure.persistence.postgres_authentication import (
    PostgresAuthentication,
)


def compose_authentication(engine: Engine) -> SimpleNamespace:
    settings = read_authentication_settings()
    tokens = JwtTokens(
        private_key=settings.private_key.get_secret_value(),
        public_keys=settings.public_keys,
        key_id=settings.key_id,
        issuer=settings.issuer,
        audience=settings.audience,
    )
    store = PostgresAuthentication(
        engine,
        issuer=settings.issuer,
        login_limit=settings.login_limit,
        address_limit=settings.address_limit,
        window_seconds=settings.window_seconds,
    )
    provider = LocalCredentials(store, parallelism=settings.hash_parallelism)
    secrets = RefreshSecrets()
    return SimpleNamespace(
        login=Login(provider, store, tokens, secrets),
        refresh=Refresh(store, tokens, secrets),
        logout=Logout(store, secrets),
        authenticate=Authenticate(tokens),
    )
