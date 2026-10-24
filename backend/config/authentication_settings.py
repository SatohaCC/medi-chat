"""Required authentication configuration; never fall back to anonymous access."""

import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from backend.project_paths import PROJECT_ROOT


class AuthenticationSettings(BaseModel):
    model_config = ConfigDict(frozen=True)
    issuer: str = Field(min_length=1)
    audience: str = Field(min_length=1)
    key_id: str = Field(min_length=1)
    private_key: SecretStr
    public_keys: dict[str, str] = Field(min_length=1)
    hash_parallelism: int = Field(default=2, ge=1, le=8)
    login_limit: int = Field(default=10, ge=1)
    address_limit: int = Field(default=60, ge=1)
    window_seconds: int = Field(default=900, ge=1)


def read_authentication_settings() -> AuthenticationSettings:
    # JSON key sets allow rotation without putting secrets into committed files.
    import json

    try:
        private = os.environ.get("AUTH_PRIVATE_KEY", "")
        key_file = os.environ.get("AUTH_PRIVATE_KEY_FILE", "")
        if private and key_file:
            raise ValueError("Specify one private key source")
        if key_file:
            path = (PROJECT_ROOT / Path(key_file)).resolve()
            if not path.is_relative_to(PROJECT_ROOT):
                raise ValueError("Private key file must be project relative")
            private = path.read_text(encoding="utf-8")
        if not private:
            raise ValueError("Private key is required")
        return AuthenticationSettings(
            issuer=os.environ["AUTH_ISSUER"],
            audience=os.environ["AUTH_AUDIENCE"],
            key_id=os.environ["AUTH_KEY_ID"],
            private_key=SecretStr(private.replace("\\n", "\n")),
            public_keys=json.loads(os.environ["AUTH_PUBLIC_KEYS"]),
            hash_parallelism=int(os.environ.get("AUTH_HASH_PARALLELISM", "2")),
            login_limit=int(os.environ.get("AUTH_LOGIN_LIMIT", "10")),
            address_limit=int(os.environ.get("AUTH_ADDRESS_LIMIT", "60")),
            window_seconds=int(os.environ.get("AUTH_LOGIN_WINDOW_SECONDS", "900")),
        )
    except KeyError, ValueError, TypeError, OSError:
        raise ValueError("Authentication configuration is missing or invalid") from None
