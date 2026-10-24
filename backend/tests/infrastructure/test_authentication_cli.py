"""Administrative commands do not require secrets in command arguments."""

import json
import sys

import pytest
from backend.infrastructure.cli.authentication import main


def test_key_generation_is_explicit_does_not_print_secrets_and_refuses_overwrite(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["authentication", "generate-keys"])
    main()
    private = (tmp_path / ".auth/private.pem").read_bytes()
    assert b"PRIVATE KEY" in private
    assert "primary" in json.loads((tmp_path / ".auth/public-keys.json").read_text())
    assert "BEGIN PRIVATE KEY" not in capsys.readouterr().out
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        main()
    assert (tmp_path / ".auth/private.pem").read_bytes() == private
