"""PG-007/008: strict initial figure inventory and CLI byte preservation."""

import pytest
from backend.application.attachment_import.import_errors import InvalidAttachment
from backend.infrastructure.cli.manage_postgres import load_inputs
from backend.tests.support.attachment_import_fixtures import xml_source


def graphic(name):
    return xml_source(
        f'<Warnings><Graphic><GraphicBody gfname="{name}"/><GraphicCaption><Lang>テスト図</Lang></GraphicCaption></Graphic></Warnings>'
    )


def test_pg007_strict_inventory_keeps_nontext_figure_bytes(tmp_path):
    (tmp_path / "テスト.xml").write_bytes(graphic("fig.gif"))
    (tmp_path / "fig.gif").write_bytes(b"GIF89a\x00\xff")
    (item,) = load_inputs(tmp_path)
    assert item.source == (tmp_path / "テスト.xml").read_bytes()
    assert item.figures[0].logical_name == "fig.gif"
    assert item.figures[0].media_type == "image/gif"
    assert item.figures[0].content == b"GIF89a\x00\xff"


@pytest.mark.parametrize(
    "name", ["missing.gif", "../unsafe.gif", "C:/unsafe.gif", "..\\unsafe.gif"]
)
def test_pg008_strict_inventory_refuses_missing_and_unsafe_assets(tmp_path, name):
    (tmp_path / "テスト.xml").write_bytes(graphic(name))
    with pytest.raises((InvalidAttachment, ValueError)):
        load_inputs(tmp_path)


def test_pg008_strict_inventory_refuses_symlink_asset(tmp_path):
    original = tmp_path / "input"
    original.mkdir()
    (original / "テスト.xml").write_bytes(graphic("fig.gif"))
    target = tmp_path / "sentinel.gif"
    target.write_bytes(b"sentinel")
    (original / "fig.gif").symlink_to(target)
    with pytest.raises(ValueError):
        load_inputs(original)
    assert target.read_bytes() == b"sentinel"
