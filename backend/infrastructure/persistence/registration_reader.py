"""公開済みSQLite世代と所有artifactの整合性を検証して読み取る。"""

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from backend.application.medicine.product_models import RegisteredMedicine
from backend.domain.attachment.value_objects import MedicineDocumentReference
from backend.domain.medicine.entities import MedicineProduct

from ...application.attachment_import.import_errors import ImportConflict
from ...application.indexing.index_errors import IndexSourceError
from ...application.indexing.index_models import IndexDocument, SourceSnapshot
from ...domain.attachment.identifiers import DocumentId
from ...domain.attachment.primitives import PmdaUrl
from ...domain.attachment.value_objects import AttachmentProductRevision
from ...domain.medicine.identifiers import YjCode
from ..index_payloads import (
    DOCUMENT_SCHEMA_VERSION,
    build_index_unit,
    registered_unit_text,
)
from ..json_payloads import parse_json_object
from .owned_sqlite import OwnedSqliteConnection
from .revision_selection import validate_active_revisions


def _checked_file(file: dict[str, str]) -> bytes:
    path = Path(file["path"])
    root = Path(file["root"])
    if (
        ".." in path.parts
        or not path.is_absolute()
        or not path.is_relative_to(root)
        or not path.resolve().is_relative_to(root)
        or any(
            parent.is_symlink()
            for parent in (path, *path.parents)
            if parent.is_relative_to(root)
        )
    ):
        raise IndexSourceError("Published artifact path is unsafe")
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != file["sha256"]:
        raise IndexSourceError("Published artifact content differs")
    return content


def read_registered_snapshot(index_path: Path) -> SourceSnapshot | None:
    try:
        with closing(
            sqlite3.connect(
                index_path.resolve().as_uri() + "?mode=ro",
                uri=True,
                factory=OwnedSqliteConnection,
            )
        ) as connection:
            connection.execute("BEGIN")
            connection.row_factory = sqlite3.Row
            table = connection.execute(
                "SELECT name FROM sqlite_master WHERE name='registration_state'"
            ).fetchone()
            if not table:
                return None
            state = connection.execute(
                "SELECT generation_id FROM registration_state WHERE singleton=1"
            ).fetchone()
            if not state:
                return None
            receipts = {
                row["version_id"]: dict(row)
                for row in connection.execute("SELECT * FROM registration_receipts")
            }
            assigned = {
                row[0]: row[1]
                for row in connection.execute(
                    "SELECT yj_code,version_id FROM active_registrations"
                )
            }
            try:
                validate_active_revisions(receipts, assigned)
            except ImportConflict as exc:
                raise IndexSourceError(exc.code) from exc
            generation = connection.execute(
                "SELECT * FROM registration_generations WHERE generation_id=?",
                (state[0],),
            ).fetchone()
            if generation is None:
                raise IndexSourceError("Published generation is missing")
            active: dict[str, list[str]] = {}
            for code, version in connection.execute(
                "SELECT yj_code,version_id FROM active_registrations ORDER BY version_id,yj_code"
            ):
                active.setdefault(version, []).append(code)
            fingerprint = hashlib.sha256(
                json.dumps(active, ensure_ascii=False, sort_keys=True).encode()
            )
            generation_files = json.loads(generation["files_json"])
            for version in sorted(active):
                receipt = connection.execute(
                    "SELECT * FROM registration_receipts WHERE version_id=?", (version,)
                ).fetchone()
                if receipt is None or receipt["artifacts_deleted"]:
                    raise IndexSourceError("Published receipt is missing or deleted")
                for file in json.loads(receipt["files_json"]):
                    content = _checked_file(file)
                    owner = connection.execute(
                        "SELECT root,sha256 FROM registration_owned_files WHERE version_id=? AND file_id=?",
                        (version, file["path"]),
                    ).fetchone()
                    if owner is None or tuple(owner) != (file["root"], file["sha256"]):
                        raise IndexSourceError("Published artifact ownership differs")
                    fingerprint.update(file["path"].encode())
                    fingerprint.update(hashlib.sha256(content).hexdigest().encode())
                name = hashlib.sha256(version.encode()).hexdigest() + ".jsonl"
                matches = [
                    file for file in generation_files if Path(file["path"]).name == name
                ]
                if len(matches) != 1:
                    raise IndexSourceError("Published projection artifact is missing")
                content = _checked_file(matches[0])
                fingerprint.update(version.encode())
                fingerprint.update(content)
            actual = "content-v1:" + fingerprint.hexdigest()
            if actual != generation["fingerprint"]:
                raise IndexSourceError("Published artifact fingerprint differs")
            value = json.loads(generation["snapshot_json"])
            for document in value["documents"]:
                if document["payload"].get("schema_version") != DOCUMENT_SCHEMA_VERSION:
                    raise ValueError(
                        "Unsupported document format; regenerate from original sources"
                    )
            for unit in value["units"]:
                registered_unit_text(parse_json_object(json.dumps(unit)))
            medicines = tuple(
                RegisteredMedicine(
                    medicine=MedicineProduct(
                        yj_code=YjCode(item["yj_code"]) if item["yj_code"] else None,
                        brand_name=item["brand_name"],
                        generic_name=item["generic_name"],
                        english_name=item["english_name"],
                        hiragana_name=item["hiragana_name"],
                    ),
                    reference=MedicineDocumentReference(
                        document_id=DocumentId(item["document_id"]),
                        pmda_url=PmdaUrl(item["pmda_url"]),
                        revision=AttachmentProductRevision(item["revision"]),
                    ),
                )
                for item in value["medicines"]
            )
            return SourceSnapshot(
                tuple(
                    IndexDocument(
                        item["document_id"],
                        parse_json_object(json.dumps(item["payload"])),
                    )
                    for item in value["documents"]
                ),
                medicines,
                tuple(
                    build_index_unit(
                        parse_json_object(json.dumps(item)), item["document_key"]
                    )
                    for item in value["units"]
                ),
                actual,
            )
    except (OSError, sqlite3.DatabaseError, ValueError, KeyError, TypeError) as exc:
        raise IndexSourceError(
            f"Published registration artifact is invalid: {exc}"
        ) from exc
