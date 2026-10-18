import pytest
from backend.config.import_settings import (
    resolve_import_directory,
    resolve_original_directory,
)
from backend.project_paths import PROJECT_ROOT


@pytest.mark.parametrize(
    "value,expected", [(None, "data/pmda/imports"), ("other/imports", "other/imports")]
)
def test_default_and_relative_import_directory_are_project_relative(
    value, expected, monkeypatch, tmp_path
):
    environ = {} if value is None else {"MEDI_CHAT_IMPORT_DIR": value}
    first = resolve_import_directory(environ=environ)
    monkeypatch.chdir(tmp_path)
    assert (
        resolve_import_directory(environ=environ)
        == first
        == (PROJECT_ROOT / expected).resolve()
    )


def test_absolute_import_directory_is_explicit(tmp_path):
    assert (
        resolve_import_directory(environ={"MEDI_CHAT_IMPORT_DIR": str(tmp_path)})
        == tmp_path.resolve()
    )


def test_original_directory_is_independent_of_structured_location(
    monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)
    assert (
        resolve_original_directory(environ={})
        == (PROJECT_ROOT / "data/pmda/originals").resolve()
    )
    assert (
        resolve_original_directory(
            environ={"MEDI_CHAT_ORIGINALS_DIR": "separate/originals"}
        )
        == (PROJECT_ROOT / "separate/originals").resolve()
    )
    assert (
        resolve_original_directory(environ={"MEDI_CHAT_ORIGINALS_DIR": str(tmp_path)})
        == tmp_path.resolve()
    )
