"""Strict local CLI transformation through the canonical domain decoder/encoder."""

import json
from pathlib import Path

from backend.application.attachment_import.errors import AttachmentImportError
from backend.application.indexing.queries.services.attachment_projection import (
    project_attachment,
)
from backend.infrastructure.package_insert_definitions.definition_assembly import (
    get_package_insert_definitions,
)
from backend.infrastructure.package_insert_definitions.definition_settings import (
    PmdaXmlSettings,
)
from backend.infrastructure.pmda_xml.pmda_artifact_encoder import PmdaArtifactEncoder
from backend.infrastructure.pmda_xml.pmda_xml_decoder import PmdaXmlDecoder
from backend.infrastructure.pmda_xml.xml_safe_parser import parse_source
from backend.project_paths import resolve_project_path


def transform(
    xml_path: Path, output_dir: Path, *, xml_settings: PmdaXmlSettings | None = None
) -> dict:
    if xml_settings is None:
        xml_settings = get_package_insert_definitions().xml_settings
    source_path = resolve_project_path(xml_path)
    target = resolve_project_path(output_dir)
    source = source_path.read_bytes()
    try:
        root, _ = parse_source(source)
        assets = {}
        for element in root.iter():
            filename = element.attrib.get("gfname")
            if not filename:
                continue
            path = (source_path.parent / filename).resolve()
            if path.is_relative_to(source_path.parent) and path.is_file():
                assets[filename] = path.read_bytes()
        decoded = PmdaXmlDecoder(
            xml_settings=xml_settings,
            assets=assets,
            strict_assets=True,
            source_filename=source_path.as_posix(),
        ).decode(source)
        bundle = PmdaArtifactEncoder().encode(
            decoded.document, project_attachment(decoded.document), decoded.source_info
        )
    except AttachmentImportError as error:
        raise ValueError(f"Transformation failed validation: {error.code}") from error
    target.mkdir(parents=True, exist_ok=True)
    for artifact in bundle.files:
        if artifact.name in {"document.json", "search_units.jsonl", "validation.json"}:
            (target / artifact.name).write_bytes(artifact.content)
    return json.loads(
        next(file.content for file in bundle.files if file.name == "validation.json")
    )
