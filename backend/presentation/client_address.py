"""Resolve login addresses without trusting caller-supplied forwarding headers."""

from ipaddress import ip_address

from fastapi import Request

from backend.application.authentication.errors import AuthenticationUnavailable
from backend.config.client_address_settings import ClientAddressSettings


def login_client_address(request: Request) -> str:
    settings: ClientAddressSettings = request.app.state.client_address_settings
    peer = request.client.host if request.client else None
    if settings.vercel:
        values = request.headers.getlist("x-vercel-forwarded-for")
        if len(values) != 1 or "," in values[0]:
            raise AuthenticationUnavailable()
        try:
            return str(ip_address(values[0].strip()))
        except ValueError:
            raise AuthenticationUnavailable() from None
    if peer is None:
        raise AuthenticationUnavailable()
    try:
        address = ip_address(peer)
    except ValueError:
        # ASGI transports may supply a non-IP literal (e.g. Unix sockets).
        if settings.trusted_proxies:
            raise AuthenticationUnavailable() from None
        return peer
    if not any(address in network for network in settings.trusted_proxies):
        return str(address)
    values = request.headers.getlist("x-forwarded-for")
    if not values or sum(map(len, values)) > 4096:
        raise AuthenticationUnavailable()
    try:
        chain = [
            ip_address(part.strip()) for value in values for part in value.split(",")
        ]
    except ValueError:
        raise AuthenticationUnavailable() from None
    for forwarded in reversed(chain):
        if not any(forwarded in network for network in settings.trusted_proxies):
            return str(forwarded)
    # No identifiable client outside the proxy network: do not share a proxy bucket.
    raise AuthenticationUnavailable()
