"""Strict RS256 access tokens and opaque refresh credentials."""

import hashlib
import secrets

import jwt

from backend.application.authentication.errors import AuthenticationRequired


class JwtTokens:
    def __init__(
        self,
        *,
        private_key: str,
        public_keys: dict[str, str],
        key_id: str,
        issuer: str,
        audience: str,
    ) -> None:
        self.private_key, self.public_keys, self.key_id = (
            private_key,
            public_keys,
            key_id,
        )
        self.issuer, self.audience = issuer, audience
        # Validate both key material and the active pair before accepting requests.
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        signing = serialization.load_pem_private_key(
            private_key.encode(), password=None
        )
        if not isinstance(signing, rsa.RSAPrivateKey) or signing.key_size < 2048:
            raise ValueError(
                "Authentication requires an RSA private key of at least 2048 bits"
            )
        for key in public_keys.values():
            public = serialization.load_pem_public_key(key.encode())
            if not isinstance(public, rsa.RSAPublicKey) or public.key_size < 2048:
                raise ValueError("Invalid authentication verification key")
        active = serialization.load_pem_public_key(public_keys[key_id].encode())
        if active.public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        ) != signing.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        ):
            raise ValueError("Authentication key pair does not match")

    def issue(self, user_id: str, now: int, absolute_expiry: int) -> str:
        if absolute_expiry <= now:
            raise AuthenticationRequired()
        return jwt.encode(
            {
                "sub": user_id,
                "iss": self.issuer,
                "aud": self.audience,
                "iat": now,
                "exp": min(now + 1800, absolute_expiry),
            },
            self.private_key,
            algorithm="RS256",
            headers={"kid": self.key_id, "typ": "at+jwt"},
        )

    def verify(self, token: str, now: int) -> tuple[str, int, int]:
        try:
            if not token or len(token) > 8192:
                raise AuthenticationRequired()
            header = jwt.get_unverified_header(token)
            if header.get("alg") != "RS256" or header.get("typ") != "at+jwt":
                raise AuthenticationRequired()
            key = self.public_keys.get(header.get("kid", ""))
            if key is None or any(k in header for k in ("jku", "jwk", "x5u", "crit")):
                raise AuthenticationRequired()
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                issuer=self.issuer,
                audience=self.audience,
                options={
                    "require": ["sub", "iss", "aud", "iat", "exp"],
                    "verify_exp": False,
                    "verify_iat": False,
                    "verify_nbf": False,
                },
            )
            issued, expires = claims["iat"], claims["exp"]
            if type(issued) is not int or type(expires) is not int or not claims["sub"]:
                raise AuthenticationRequired()
            if not issued <= now or not 0 < expires - issued <= 1800:
                raise AuthenticationRequired()
            if "nbf" in claims and (
                type(claims["nbf"]) is not int or claims["nbf"] > now
            ):
                raise AuthenticationRequired()
            if expires <= now:
                raise AuthenticationRequired("access_expired")
            return claims["sub"], issued, expires
        except jwt.PyJWTError, TypeError, ValueError, KeyError:
            raise AuthenticationRequired() from None


class RefreshSecrets:
    def generate(self) -> str:
        return secrets.token_urlsafe(48)

    def digest(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()
