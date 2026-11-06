"""Explicit trust boundary for authentication client addresses."""

import os
from dataclasses import dataclass
from ipaddress import IPv4Network, IPv6Network, ip_network


@dataclass(frozen=True)
class ClientAddressSettings:
    trusted_proxies: tuple[IPv4Network | IPv6Network, ...] = ()
    vercel: bool = False


def read_client_address_settings() -> ClientAddressSettings:
    raw = os.environ.get("AUTH_TRUSTED_PROXIES", "")
    try:
        networks = (
            tuple(ip_network(value.strip()) for value in raw.split(",")) if raw else ()
        )
        if any(network.prefixlen == 0 for network in networks):
            raise ValueError("Unrestricted proxy trust is not allowed")
        vercel = os.environ.get("VERCEL") == "1"
        if vercel and networks:
            raise ValueError("Vercel owns the proxy trust boundary")
        return ClientAddressSettings(networks, vercel)
    except ValueError:
        raise ValueError("Invalid authentication proxy configuration") from None
