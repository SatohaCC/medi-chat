"""Explicit administrative CLI; passwords never travel in arguments."""

import argparse
import getpass
import json
import os
import time
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from backend.application.authentication.commands.manage_users import (
    ProvisionUser,
    ResetPassword,
    StopUser,
)
from backend.application.authentication.errors import (
    AuthenticationUnavailable,
    LoginLimited,
)
from backend.config.authentication_settings import read_authentication_settings
from backend.config.database_settings import resolve_postgres_database_settings
from backend.config.runtime_environment import load_runtime_environment
from backend.infrastructure.authentication.credentials import LocalCredentials
from backend.infrastructure.authentication.tokens import RefreshSecrets
from backend.infrastructure.persistence.postgres_authentication import (
    PostgresAuthentication,
)
from backend.infrastructure.persistence.postgres_engine import create_postgres_engine


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage medi-chat login accounts")
    parser.add_argument(
        "operation",
        choices=("generate-keys", "create", "stop", "reset-password", "cleanup"),
    )
    args = parser.parse_args()
    if args.operation == "generate-keys":
        directory = Path(".auth")
        directory.mkdir(mode=0o700, exist_ok=True)
        private_path, public_path = (
            directory / "private.pem",
            directory / "public-keys.json",
        )
        if private_path.exists() or public_path.exists():
            raise SystemExit("Key files already exist; refusing to overwrite")
        key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
        private = key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        public = (
            key.public_key()
            .public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode()
        )
        descriptor = os.open(private_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as file:
            file.write(private)
        with public_path.open("x", encoding="utf-8") as file:
            json.dump({"primary": public}, file)
        print(
            "Keys written to .auth/private.pem and .auth/public-keys.json; set FastAPI-only AUTH variables"
        )
        return
    load_runtime_environment()
    settings = resolve_postgres_database_settings()
    auth = read_authentication_settings()
    engine = create_postgres_engine(settings.database_url)
    try:
        store = PostgresAuthentication(
            engine, issuer=auth.issuer, window_seconds=auth.window_seconds
        )
        if args.operation == "cleanup":
            print(f"Expired sessions removed: {store.cleanup(int(time.time()))}")
            return
        login_id = input("Login ID: ")
        if args.operation == "stop":
            found = StopUser(store).execute(login_id)
        else:
            password = getpass.getpass("Password (15-128 characters): ")
            if password != getpass.getpass("Confirm password: "):
                raise ValueError("Passwords do not match")
            hashing = LocalCredentials(store, parallelism=1)
            if args.operation == "create":
                ProvisionUser(store, hashing, RefreshSecrets()).execute(
                    login_id, password
                )
                found = True
            else:
                found = ResetPassword(store, hashing).execute(login_id, password)
        if not found:
            raise ValueError("Account not found")
        print("Account operation completed")
    except AuthenticationUnavailable, LoginLimited:
        raise SystemExit(
            "Account operation failed; check storage availability and duplicate login IDs"
        ) from None
    except ValueError as error:
        raise SystemExit(str(error)) from None
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
