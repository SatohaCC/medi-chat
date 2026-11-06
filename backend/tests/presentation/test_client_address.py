"""Client-address trust and rate-limit inputs at the HTTP boundary."""

from ipaddress import ip_network
from types import SimpleNamespace

import pytest
from backend.application.authentication.errors import AuthenticationUnavailable
from backend.config.client_address_settings import (
    ClientAddressSettings,
    read_client_address_settings,
)
from backend.presentation.client_address import login_client_address
from starlette.requests import Request


def request(peer, headers=(), *, proxies=(), vercel=False):
    settings = ClientAddressSettings(
        tuple(ip_network(value) for value in proxies), vercel
    )
    return Request(
        {
            "type": "http",
            "client": (peer, 1234) if peer else None,
            "headers": [(key.encode(), value.encode()) for key, value in headers],
            "app": SimpleNamespace(
                state=SimpleNamespace(client_address_settings=settings)
            ),
        }
    )


def test_direct_client_ignores_spoofed_forwarding_headers():
    assert (
        login_client_address(
            request(
                "198.51.100.2",
                [
                    ("x-forwarded-for", "203.0.113.9"),
                    ("x-vercel-forwarded-for", "203.0.113.8"),
                ],
            )
        )
        == "198.51.100.2"
    )


def test_trusted_proxy_clients_are_distinct_and_left_spoof_is_ignored():
    for client in ("198.51.100.2", "198.51.100.3"):
        assert (
            login_client_address(
                request(
                    "10.0.0.1",
                    [("x-forwarded-for", f"203.0.113.9, {client}, 10.0.0.2")],
                    proxies=("10.0.0.0/24",),
                )
            )
            == client
        )


def test_duplicate_headers_follow_right_to_left_trust_chain():
    assert (
        login_client_address(
            request(
                "10.0.0.1",
                [
                    ("x-forwarded-for", "203.0.113.9"),
                    ("x-forwarded-for", "198.51.100.2"),
                ],
                proxies=("10.0.0.1",),
            )
        )
        == "198.51.100.2"
    )


def test_ipv6_is_canonicalized():
    assert (
        login_client_address(
            request("::1", [("x-forwarded-for", "2001:0db8::1")], proxies=("::1",))
        )
        == "2001:db8::1"
    )


@pytest.mark.parametrize(
    "headers",
    [
        (),
        (("x-forwarded-for", ""),),
        (("x-forwarded-for", "unknown"),),
        (("x-forwarded-for", "10.0.0.2"),),
        (("x-forwarded-for", "198.51.100.2,"),),
    ],
)
def test_unusable_trusted_proxy_address_fails_closed(headers):
    with pytest.raises(AuthenticationUnavailable):
        login_client_address(request("10.0.0.1", headers, proxies=("10.0.0.0/24",)))


def test_missing_peer_does_not_share_unknown_bucket():
    with pytest.raises(AuthenticationUnavailable):
        login_client_address(request(None))


def test_vercel_uses_platform_header_only():
    assert (
        login_client_address(
            request(
                "10.0.0.1",
                [
                    ("x-forwarded-for", "203.0.113.9"),
                    ("x-vercel-forwarded-for", "198.51.100.2"),
                ],
                vercel=True,
            )
        )
        == "198.51.100.2"
    )


@pytest.mark.parametrize(
    "headers",
    [
        (),
        (("x-vercel-forwarded-for", "bad"),),
        (("x-vercel-forwarded-for", "198.51.100.2, 203.0.113.9"),),
        (
            ("x-vercel-forwarded-for", "198.51.100.2"),
            ("x-vercel-forwarded-for", "203.0.113.9"),
        ),
    ],
)
def test_vercel_missing_or_invalid_platform_header_fails_closed(headers):
    with pytest.raises(AuthenticationUnavailable):
        login_client_address(request("10.0.0.1", headers, vercel=True))


@pytest.mark.parametrize(
    "value", ["*", "0.0.0.0/0", "::/0", "host.example", "10.0.0.1,", "10.0.0.1/24"]
)
def test_invalid_proxy_settings_are_rejected(monkeypatch, value):
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.setenv("AUTH_TRUSTED_PROXIES", value)
    with pytest.raises(ValueError, match="proxy configuration"):
        read_client_address_settings()


def test_proxy_configuration_and_vercel_are_exclusive(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("AUTH_TRUSTED_PROXIES", "10.0.0.1")
    with pytest.raises(ValueError):
        read_client_address_settings()


def test_default_and_explicit_proxy_settings(monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("AUTH_TRUSTED_PROXIES", raising=False)
    assert read_client_address_settings() == ClientAddressSettings()
    monkeypatch.setenv("AUTH_TRUSTED_PROXIES", "10.0.0.1, ::1/128")
    assert len(read_client_address_settings().trusted_proxies) == 2


def test_application_wires_explicit_proxy_configuration(monkeypatch):
    from backend.main import create_app

    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.setenv("AUTH_TRUSTED_PROXIES", "10.0.0.1")
    app = create_app()
    assert app.state.client_address_settings.trusted_proxies == (
        ip_network("10.0.0.1"),
    )


def test_application_rejects_invalid_proxy_configuration(monkeypatch):
    from backend.main import create_app

    monkeypatch.setenv("AUTH_TRUSTED_PROXIES", "*")
    with pytest.raises(ValueError, match="proxy configuration"):
        create_app()
