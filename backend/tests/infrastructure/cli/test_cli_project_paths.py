"""CLIの入力・生成先が実行ディレクトリに依存しない。"""

import json
import shutil
import sys
from pathlib import Path

import pytest
from backend import project_paths
from backend.infrastructure.cli import build_autocomplete_index, structure_pmda_xml


@pytest.mark.source_data
@pytest.mark.parametrize("batch", [False, True])
@pytest.mark.parametrize("other_cwd", [False, True])
def test_xml_cli_uses_project_relative_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    batch: bool,
    other_cwd: bool,
) -> None:
    root = tmp_path / "project"
    source = root / "data/pmda/originals"
    source.mkdir(parents=True)
    original = (
        project_paths.PROJECT_ROOT
        / "data/pmda/originals/イグザレルト錠２．５ｍｇ/630004_3339003F5020_1_08.xml"
    )
    xml = source / original.name
    shutil.copytree(original.parent, source, dirs_exist_ok=True)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.setattr(project_paths, "PROJECT_ROOT", root)
    monkeypatch.setattr("backend.infrastructure.pmda_xml.xml_nodes.PROJECT_ROOT", root)
    monkeypatch.chdir(elsewhere if other_cwd else root)
    inputs = (
        ["--source-dir", "data/pmda/originals"]
        if batch
        else [f"data/pmda/originals/{xml.name}"]
    )
    monkeypatch.setattr(
        sys, "argv", ["structure_pmda_xml", *inputs, "--output-dir", "output"]
    )
    assert structure_pmda_xml.main() == 0
    report = json.loads(capsys.readouterr().out)
    if batch:
        assert report["results"][0]["xml"] == f"data/pmda/originals/{xml.name}"
    output = root / "output"
    documents = list(output.rglob("document.json"))
    assert len(documents) == 1
    assert json.loads(documents[0].read_text(encoding="utf-8"))
    assert not (elsewhere / "output").exists()


@pytest.mark.parametrize("explicit", [False, True])
@pytest.mark.parametrize("other_cwd", [False, True])
def test_autocomplete_cli_uses_project_relative_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, explicit: bool, other_cwd: bool
) -> None:
    root = tmp_path / "project"
    source = root / "yj"
    source.mkdir(parents=True)
    (source / "y_ALL_sample.csv").write_text("", encoding="cp932")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.setattr(project_paths, "PROJECT_ROOT", root)
    monkeypatch.setattr(build_autocomplete_index, "PROJECT_ROOT", root)
    monkeypatch.chdir(elsewhere if other_cwd else root)
    options = (
        ["--csv-path", "yj/y_ALL_sample.csv", "--output", "output/medicines.json"]
        if explicit
        else []
    )
    monkeypatch.setattr(sys, "argv", ["build_autocomplete_index", *options])
    build_autocomplete_index.main()
    outputs = (
        [root / "output/medicines.json"]
        if explicit
        else [
            root / "frontend/public/data/medicines.json",
            root / "data/pmda/structured/medicines_autocomplete.json",
        ]
    )
    for output in outputs:
        assert json.loads(output.read_text(encoding="utf-8")) == []
    assert list(elsewhere.iterdir()) == []
