"""Missing production secrets never enable anonymous access."""

import pytest
from backend.config.authentication_settings import read_authentication_settings


@pytest.mark.parametrize(
    "missing", ["AUTH_PRIVATE_KEY", "AUTH_PUBLIC_KEYS", "AUTH_ISSUER", "AUTH_KEY_ID"]
)
def test_missing_authentication_settings_are_rejected(monkeypatch, missing):
    monkeypatch.delenv(missing, raising=False)
    with pytest.raises(ValueError, match="missing or invalid"):
        read_authentication_settings()


def test_invalid_settings_do_not_print_secret_input(monkeypatch):
    monkeypatch.setenv("AUTH_PRIVATE_KEY", "test-secret-never-print")
    monkeypatch.setenv("AUTH_PUBLIC_KEYS", "not-json")
    with pytest.raises(ValueError) as error:
        read_authentication_settings()
    assert "test-secret-never-print" not in str(error.value)


def test_local_key_file_is_read_only_by_backend(monkeypatch, tmp_path):
    from backend.config import authentication_settings as settings

    monkeypatch.setattr(settings, "PROJECT_ROOT", tmp_path)
    monkeypatch.delenv("AUTH_PRIVATE_KEY", raising=False)
    path = tmp_path / "private.pem"
    path.write_text("local-private-pem", encoding="utf-8")
    monkeypatch.setenv("AUTH_PRIVATE_KEY_FILE", "private.pem")
    assert (
        settings.read_authentication_settings().private_key.get_secret_value()
        == "local-private-pem"
    )


def test_private_key_file_cannot_escape_project(monkeypatch):
    monkeypatch.delenv("AUTH_PRIVATE_KEY", raising=False)
    monkeypatch.setenv("AUTH_PRIVATE_KEY_FILE", "../outside.pem")
    with pytest.raises(ValueError, match="missing or invalid"):
        read_authentication_settings()
