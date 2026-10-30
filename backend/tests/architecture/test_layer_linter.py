"""Regression coverage for the static layer linter's package discovery."""

from pathlib import Path

import pytest
from scripts.checks.layer_architecture import check


@pytest.mark.parametrize(
    "layer", ["domain", "application", "infrastructure", "presentation", "config"]
)
def test_layer_root_requires_initializer(tmp_path: Path, layer: str) -> None:
    package = tmp_path / "backend" / layer
    package.mkdir(parents=True)
    (package / "module.py").write_text("", encoding="utf-8")

    assert any(
        finding.rule == "LAY002" and finding.path == f"backend/{layer}"
        for finding in check(tmp_path)
    )

    (package / "__init__.py").write_text("", encoding="utf-8")
    assert not any(finding.rule == "LAY002" for finding in check(tmp_path))


@pytest.mark.parametrize("package", ["presentation", "presentation/nested"])
def test_response_conversion_in_initializer_is_rejected(
    tmp_path: Path, package: str
) -> None:
    directory = tmp_path / "backend" / package
    directory.mkdir(parents=True)
    (directory / "__init__.py").write_text(
        "from backend.presentation.chat_models import ChatResponse\n"
        "from backend.application.chat.queries.models import ChatResult\n"
        "def reverse(response: ChatResponse) -> ChatResult:\n"
        "    return ChatResult()\n",
        encoding="utf-8",
    )

    assert any(
        finding.rule == "LAY006" and finding.path == f"backend/{package}/__init__.py"
        for finding in check(tmp_path)
    )


@pytest.mark.parametrize("directory", ["__pycache__", ".generated"])
def test_generated_directories_are_excluded(tmp_path: Path, directory: str) -> None:
    generated = tmp_path / "backend" / "presentation" / directory
    generated.mkdir(parents=True)
    (generated / "invalid.py").write_text("invalid syntax!", encoding="utf-8")

    assert not check(tmp_path)
