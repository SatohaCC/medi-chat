"""Authentication failures without HTTP or provider details."""


class AuthenticationRequired(Exception):
    def __init__(self, code: str = "authentication_required") -> None:
        self.code = code
        super().__init__(code)


class LoginLimited(Exception):
    """Shared login attempt budget exhausted."""


class AuthenticationUnavailable(Exception):
    """Credential storage failed without exposing database details."""
