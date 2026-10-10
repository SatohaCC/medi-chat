"""構造化添付文書ファイルを索引用の値へ変換する境界。"""

import hashlib
import json
from pathlib import Path

from ...application.indexing.index_errors import IndexSourceError
from ...application.indexing.index_models import (
    IndexDocument,
    IndexUnit,
    SourceSnapshot,
)
from ...domain.attachment.entities import AttachmentProductRecord
from ..index_payloads import build_index_document, build_index_unit
from ..json_payloads import parse_json_object


class FileIndexSourceReader:
    def __init__(self, structured_dir: Path) -> None:
        self._structured_dir = structured_dir.resolve()

    def read_snapshot(self) -> SourceSnapshot:
        paths = self._document_unit_paths()
        fingerprint = self._source_fingerprint(paths)
        documents: list[IndexDocument] = []
        medicines: list[AttachmentProductRecord] = []
        units: list[IndexUnit] = []
        for document_path, units_path in paths:
            document, document_medicines = self._read_document(document_path)
            documents.append(document)
            medicines.extend(document_medicines)
            units.extend(self._read_units(units_path, document.document_id))
        return SourceSnapshot(
            tuple(documents), tuple(medicines), tuple(units), fingerprint
        )

    def _document_unit_paths(self) -> list[tuple[Path, Path]]:
        if not self._structured_dir.is_dir():
            raise IndexSourceError(
                f"Structured data directory does not exist: {self._structured_dir}"
            )
        manifest_path = self._structured_dir / "manifest.json"
        if manifest_path.is_file():
            try:
                manifest = parse_json_object(manifest_path.read_text(encoding="utf-8"))
            except OSError, json.JSONDecodeError:
                pass
            else:
                count = manifest.get("document_count", 0)
                if not isinstance(count, (int, float)):
                    raise IndexSourceError(f"Invalid document_count in {manifest_path}")
                if count <= 0:
                    raise IndexSourceError(
                        f"No structured documents listed in manifest at: {self._structured_dir}"
                    )
        paths: list[tuple[Path, Path]] = []
        for document_path in sorted(self._structured_dir.glob("*/document.json")):
            units_path = document_path.parent / "search_units.jsonl"
            if not units_path.is_file():
                raise IndexSourceError(
                    f"Missing search units {units_path} beside {document_path}"
                )
            paths.append((document_path, units_path))
        if not paths:
            raise IndexSourceError(
                f"No structured documents found under: {self._structured_dir}"
            )
        return paths

    @staticmethod
    def _read_document(
        document_path: Path,
    ) -> tuple[IndexDocument, list[AttachmentProductRecord]]:
        try:
            payload = parse_json_object(document_path.read_text(encoding="utf-8"))
            return build_index_document(payload)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise IndexSourceError(
                f"Invalid structured document at {document_path}: {exc}"
            ) from exc

    @staticmethod
    def _read_units(units_path: Path, document_id: str) -> list[IndexUnit]:
        units: list[IndexUnit] = []
        section_codes: set[str] = set()
        unit_ids: set[str] = set()
        try:
            with units_path.open("r", encoding="utf-8") as stream:
                for line_number, line in enumerate(stream, start=1):
                    if not line.strip():
                        continue
                    try:
                        payload = parse_json_object(line)
                        if payload.get("document_key") != document_id:
                            raise IndexSourceError(
                                f"Document key mismatch at {units_path}:{line_number}"
                            )
                        if not payload.get("unit_id"):
                            raise IndexSourceError(
                                f"Missing unit_id at {units_path}:{line_number}"
                            )
                        unit = build_index_unit(payload, document_id)
                        if unit.unit_id in unit_ids:
                            raise ValueError("Duplicate unit_id")
                        if unit.kind == "section":
                            if (
                                not unit.section_code
                                or unit.section_code in section_codes
                            ):
                                raise ValueError("Missing or duplicate section code")
                            if unit.unit_id != f"{document_id}:{unit.section_code}":
                                raise ValueError(
                                    "Section unit_id does not match its section code"
                                )
                            section_codes.add(unit.section_code)
                        unit_ids.add(unit.unit_id)
                        units.append(unit)
                    except (ValueError, TypeError, KeyError) as exc:
                        raise IndexSourceError(
                            f"Invalid JSONL at {units_path}:{line_number}: {exc}"
                        ) from exc
        except OSError as exc:
            raise IndexSourceError(f"Could not read {units_path}: {exc}") from exc
        return units

    def _source_fingerprint(self, paths: list[tuple[Path, Path]]) -> str:
        # A manifest can remain unchanged when an individual JSONL is regenerated.
        # Hash the actual inputs so an old cell-level index cannot appear current.
        digest = hashlib.sha256()
        manifest_path = self._structured_dir / "manifest.json"
        source_paths = [path for pair in paths for path in pair]
        if manifest_path.is_file():
            source_paths.append(manifest_path)
        for path in source_paths:
            try:
                content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError as exc:
                raise IndexSourceError(f"Could not read {path}: {exc}") from exc
            digest.update(
                path.relative_to(self._structured_dir).as_posix().encode("utf-8")
            )
            digest.update(b"\0")
            digest.update(content_hash.encode("ascii"))
            digest.update(b"\0")
        return f"content-v1:{digest.hexdigest()}"
