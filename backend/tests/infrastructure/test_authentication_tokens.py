"""AUTH-01/03/06/26: verify the actual cryptographic boundary."""

import time

import jwt
import pytest
from backend.application.authentication.errors import AuthenticationRequired
from backend.infrastructure.authentication.tokens import JwtTokens
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


@pytest.fixture
def signing_keys():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return (
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode(),
        key.public_key()
        .public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        .decode(),
    )


@pytest.fixture
def tokens(signing_keys):
    return JwtTokens(
        private_key=signing_keys[0],
        public_keys={"test": signing_keys[1]},
        key_id="test",
        issuer="https://test.invalid",
        audience="medi-chat",
    )


def test_access_lifetime_and_absolute_session_limit(tokens):
    now = int(time.time())
    token = tokens.issue("user", now, now + 604800)
    assert tokens.verify(token, now) == ("user", now, now + 1800)
    assert tokens.verify(tokens.issue("user", now, now + 9), now)[2] == now + 9
    with pytest.raises(AuthenticationRequired):
        tokens.verify(token, now + 1800)


@pytest.mark.parametrize(
    "change",
    [
        {"iss": "evil"},
        {"aud": "other"},
        {"exp": 1},
        {"sub": ""},
        {"iat": 9999999999},
        {"exp": 9999999999},
    ],
)
def test_invalid_claims_are_rejected(tokens, signing_keys, change):
    now = int(time.time())
    claims = {
        "iss": "https://test.invalid",
        "aud": "medi-chat",
        "sub": "user",
        "iat": now,
        "exp": now + 1800,
    }
    claims.update(change)
    token = jwt.encode(
        claims,
        signing_keys[0],
        algorithm="RS256",
        headers={"kid": "test", "typ": "at+jwt"},
    )
    with pytest.raises(AuthenticationRequired):
        tokens.verify(token, now)


@pytest.mark.parametrize(
    "headers", [{"kid": "unknown", "typ": "at+jwt"}, {"kid": "test", "typ": "JWT"}]
)
def test_unknown_key_and_wrong_purpose(tokens, signing_keys, headers):
    now = int(time.time())
    token = jwt.encode(
        {
            "sub": "user",
            "iat": now,
            "exp": now + 30,
            "iss": "https://test.invalid",
            "aud": "medi-chat",
        },
        signing_keys[0],
        algorithm="RS256",
        headers=headers,
    )
    with pytest.raises(AuthenticationRequired):
        tokens.verify(token, now)


def test_tampering_and_unsigned_token(tokens):
    now = int(time.time())
    token = tokens.issue("user", now, now + 604800)
    for invalid in ("", token + "x", jwt.encode({"sub": "user"}, "", algorithm="none")):
        with pytest.raises(AuthenticationRequired):
            tokens.verify(invalid, now)


def test_rotation_accepts_retained_old_key_and_rejects_removed_key(signing_keys):
    old_private, old_public = signing_keys
    new = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    new_private = new.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    new_public = (
        new.public_key()
        .public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        .decode()
    )
    now = int(time.time())
    old = JwtTokens(
        private_key=old_private,
        public_keys={"old": old_public},
        key_id="old",
        issuer="issuer",
        audience="api",
    )
    retained = JwtTokens(
        private_key=new_private,
        public_keys={"new": new_public, "old": old_public},
        key_id="new",
        issuer="issuer",
        audience="api",
    )
    old_token = old.issue("user", now, now + 1800)
    assert retained.verify(old_token, now)[0] == "user"
    removed = JwtTokens(
        private_key=new_private,
        public_keys={"new": new_public},
        key_id="new",
        issuer="issuer",
        audience="api",
    )
    with pytest.raises(AuthenticationRequired):
        removed.verify(old_token, now)
