"""Revoke the refresh family even after the access JWT has expired."""

from backend.application.authentication.interfaces.sessions import Sessions
from backend.application.authentication.interfaces.tokens import TokenSecrets


class Logout:
    def __init__(self, sessions: Sessions, secrets: TokenSecrets) -> None:
        self.sessions, self.secrets = sessions, secrets

    def execute(self, token: str) -> None:
        if token and len(token) <= 256:
            self.sessions.revoke(self.secrets.digest(token))
