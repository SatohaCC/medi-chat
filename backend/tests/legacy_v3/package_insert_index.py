"""構造化JSON/JSONLから添付文書の検索索引を構築・更新する。"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from backend.domain.shared.services import normalize_search_text

from .package_insert_errors import PackageInsertStoreError
from .sqlite_database import SQLiteDatabase


class PackageInsertIndexBuilder:
    SCHEMA_VERSION = "3"

    def __init__(self, structured_dir: Path, database: SQLiteDatabase) -> None:
        self.database = database
        self.structured_dir = structured_dir.resolve()
        if not self.structured_dir.is_dir():
            raise PackageInsertStoreError(
                f"Structured data directory does not exist: {self.structured_dir}"
            )
        self._document_unit_paths: list[tuple[Path, Path]] | None = None
        manifest_path = self.structured_dir / "manifest.json"
        if manifest_path.is_file():
            try:
                manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
                if manifest_data.get("document_count", 0) <= 0:
                    raise PackageInsertStoreError(
                        f"No structured documents listed in manifest at: {self.structured_dir}"
                    )
            except (OSError, json.JSONDecodeError):
                pass
        else:
            if not self.document_unit_paths:
                raise PackageInsertStoreError(
                    f"No structured documents found under: {self.structured_dir}"
                )

    @property
    def document_unit_paths(self) -> list[tuple[Path, Path]]:
        if self._document_unit_paths is None:
            self._document_unit_paths = self._find_document_unit_paths()
        return self._document_unit_paths

    def _find_document_unit_paths(self) -> list[tuple[Path, Path]]:
        pairs = []
        for document_path in sorted(self.structured_dir.glob("*/document.json")):
            units_path = document_path.parent / "search_units.jsonl"
            if not units_path.is_file():
                raise PackageInsertStoreError(
                    f"Missing search units beside {document_path}"
                )
            pairs.append((document_path, units_path))
        return pairs

    @staticmethod
    def _get_latest_revision(revisions: list[dict[str, Any]]) -> dict[str, Any]:
        if not revisions:
            return {}
        return revisions[-1]

    def _compute_source_fingerprint(self) -> str:
        manifest_path = self.structured_dir / "manifest.json"
        if manifest_path.is_file():
            stat = manifest_path.stat()
            return f"manifest:{stat.st_size}:{stat.st_mtime_ns}:{manifest_path.read_text(encoding='utf-8').strip()}"
        parts = []
        for document_path, units_path in self.document_unit_paths:
            for path in (document_path, units_path):
                stat = path.stat()
                parts.append(f"{path.as_posix()}|{stat.st_size}|{stat.st_mtime_ns}")
        return "\n".join(parts)

    def build_if_needed(self) -> None:
        self.database.index_path.parent.mkdir(parents=True, exist_ok=True)
        fingerprint = self._compute_source_fingerprint()
        try:
            with self.database.transaction() as connection:
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS index_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
                )
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS documents (document_key TEXT PRIMARY KEY, payload_json TEXT NOT NULL)"
                )
                connection.execute(
                    """CREATE TABLE IF NOT EXISTS medicines (
                        document_key TEXT NOT NULL,
                        yj_code TEXT,
                        brand_name TEXT NOT NULL,
                        generic_name TEXT NOT NULL,
                        english_name TEXT NOT NULL,
                        hiragana_name TEXT NOT NULL,
                        pmda_url TEXT NOT NULL,
                        revision_json TEXT NOT NULL
                    )"""
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_medicines_yj ON medicines(yj_code)"
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_medicines_doc ON medicines(document_key)"
                )
                connection.execute(
                    """CREATE TABLE IF NOT EXISTS units (
                        unit_id TEXT PRIMARY KEY,
                        document_key TEXT NOT NULL,
                        section_code TEXT NOT NULL,
                        kind TEXT NOT NULL,
                        payload_json TEXT NOT NULL
                    )"""
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS units_by_document_section ON units(document_key, section_code, kind)"
                )
                connection.execute(
                    """CREATE VIRTUAL TABLE IF NOT EXISTS unit_fts USING fts5(
                        unit_id UNINDEXED,
                        document_key UNINDEXED,
                        section_code UNINDEXED,
                        kind UNINDEXED,
                        query_text,
                        drug_name,
                        tokenize='trigram'
                    )"""
                )
                current = connection.execute(
                    "SELECT value FROM index_meta WHERE key='source_fingerprint'"
                ).fetchone()
                current_schema = connection.execute(
                    "SELECT value FROM index_meta WHERE key='schema_version'"
                ).fetchone()
                if (
                    current
                    and current["value"] == fingerprint
                    and current_schema
                    and current_schema["value"] == self.SCHEMA_VERSION
                ):
                    return
                connection.execute("DELETE FROM unit_fts")
                connection.execute("DELETE FROM units")
                connection.execute("DELETE FROM medicines")
                connection.execute("DELETE FROM documents")
                medicine_batch: list[
                    tuple[str, str | None, str, str, str, str, str, str]
                ] = []
                for document_path, units_path in self.document_unit_paths:
                    document_payload = json.loads(
                        document_path.read_text(encoding="utf-8")
                    )
                    document_meta = document_payload.get("document") or {}
                    source_meta = document_payload.get("source") or {}
                    company = document_meta.get("company_identifier")
                    insert_no = document_meta.get("package_insert_no")
                    document_key = (
                        f"{company}_{insert_no}" if company and insert_no else None
                    )
                    if not document_key:
                        raise PackageInsertStoreError(
                            f"Missing package insert number in {document_path}"
                        )
                    connection.execute(
                        "INSERT INTO documents(document_key, payload_json) VALUES (?, ?)",
                        (
                            document_key,
                            json.dumps(document_payload, ensure_ascii=False),
                        ),
                    )
                    revision = self._get_latest_revision(
                        document_meta.get("revisions") or []
                    )
                    for product in document_meta.get("products") or []:
                        medicine_batch.append(
                            (
                                document_key,
                                product.get("yj_code"),
                                product.get("brand_name") or "",
                                document_meta.get("generic_name") or "",
                                product.get("english_name") or "",
                                product.get("hiragana_name") or "",
                                source_meta.get("pmda_url")
                                or document_meta.get("pmda_url")
                                or "",
                                json.dumps(revision, ensure_ascii=False),
                            )
                        )
                    if len(medicine_batch) >= 500:
                        connection.executemany(
                            """INSERT INTO medicines (
                                document_key, yj_code, brand_name, generic_name,
                                english_name, hiragana_name, pmda_url, revision_json
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                            medicine_batch,
                        )
                        medicine_batch.clear()

                    batch: list[tuple[str, str, str, str, str, str, str]] = []
                    with units_path.open("r", encoding="utf-8") as stream:
                        for line_number, line in enumerate(stream, start=1):
                            if not line.strip():
                                continue
                            try:
                                unit = json.loads(line)
                            except json.JSONDecodeError as exc:
                                raise PackageInsertStoreError(
                                    f"Invalid JSONL at {units_path}:{line_number}: {exc}"
                                ) from exc
                            if unit.get("document_key") != document_key:
                                raise PackageInsertStoreError(
                                    f"Document key mismatch at {units_path}:{line_number}"
                                )
                            columns = unit.get("columns") or {}
                            searchable = [
                                unit.get("text", ""),
                                " ".join(unit.get("context_labels") or []),
                                (unit.get("section") or {}).get("title", ""),
                                " ".join(str(value) for value in columns.values()),
                            ]
                            query_text = normalize_search_text(" ".join(searchable))
                            drug_name = normalize_search_text(
                                str(columns.get("drug_name", ""))
                            )
                            unit_id = unit.get("unit_id")
                            if not unit_id:
                                raise PackageInsertStoreError(
                                    f"Missing unit_id at {units_path}:{line_number}"
                                )
                            section_code = str(
                                (unit.get("section") or {}).get("code", "")
                            )
                            kind = str(unit.get("kind", ""))
                            batch.append(
                                (
                                    unit_id,
                                    document_key,
                                    section_code,
                                    kind,
                                    json.dumps(unit, ensure_ascii=False),
                                    query_text,
                                    drug_name,
                                )
                            )
                            if len(batch) >= 500:
                                self._insert_search_unit_batch(connection, batch)
                                batch.clear()
                    if batch:
                        self._insert_search_unit_batch(connection, batch)

                if medicine_batch:
                    connection.executemany(
                        """INSERT INTO medicines (
                            document_key, yj_code, brand_name, generic_name,
                            english_name, hiragana_name, pmda_url, revision_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        medicine_batch,
                    )
                connection.execute(
                    "INSERT OR REPLACE INTO index_meta(key, value) VALUES ('source_fingerprint', ?)",
                    (fingerprint,),
                )
                connection.execute(
                    "INSERT OR REPLACE INTO index_meta(key, value) VALUES ('schema_version', ?)",
                    (self.SCHEMA_VERSION,),
                )
        except (sqlite3.Error, OSError, json.JSONDecodeError) as exc:
            raise PackageInsertStoreError(
                f"Could not build local search index: {exc}"
            ) from exc

    @staticmethod
    def _insert_search_unit_batch(
        connection: sqlite3.Connection,
        batch: list[tuple[str, str, str, str, str, str, str]],
    ) -> None:
        connection.executemany(
            "INSERT INTO units(unit_id, document_key, section_code, kind, payload_json) VALUES (?, ?, ?, ?, ?)",
            [row[:5] for row in batch],
        )
        connection.executemany(
            """INSERT INTO unit_fts(
                unit_id, document_key, section_code, kind, query_text, drug_name
            ) VALUES (?, ?, ?, ?, ?, ?)""",
            [(row[0], row[1], row[2], row[3], row[5], row[6]) for row in batch],
        )
