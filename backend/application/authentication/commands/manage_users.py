"""Trusted user lifecycle commands; no public registration endpoint."""

from backend.application.authentication.interfaces.administration import (
    PasswordHashing,
    UserAdministration,
)
from backend.application.authentication.interfaces.tokens import TokenSecrets
from backend.domain.identity.entities import User
from backend.domain.identity.identifiers import UserId
from backend.domain.identity.primitives import LoginId, Password


class ProvisionUser:
    def __init__(
        self, store: UserAdministration, hashing: PasswordHashing, secrets: TokenSecrets
    ) -> None:
        self.store, self.hashing, self.secrets = store, hashing, secrets

    def execute(self, login_id: str, password: str) -> str:
        user = User(user_id=UserId.generate(), login_id=LoginId(login_id))
        secret = Password(password)
        self.store.provision(
            str(user.user_id),
            user.login_id.value,
            self.hashing.hash(secret.value),
            self.secrets.generate(),
        )
        return str(user.user_id)


class StopUser:
    def __init__(self, store: UserAdministration) -> None:
        self.store = store

    def execute(self, login_id: str) -> bool:
        return self.store.manage(LoginId(login_id).value)


class ResetPassword:
    def __init__(self, store: UserAdministration, hashing: PasswordHashing) -> None:
        self.store, self.hashing = store, hashing

    def execute(self, login_id: str, password: str) -> bool:
        return self.store.manage(
            LoginId(login_id).value,
            password_hash=self.hashing.hash(Password(password).value),
        )
