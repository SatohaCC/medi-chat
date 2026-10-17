"""正本Core reader、索引物理構造、入力fingerprintの回帰。"""

from __future__ import annotations

import asyncio
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from backend.application.medicine.product_catalog import MedicineCatalog
from backend.application.medicine.product_models import RegisteredMedicine
from backend.infrastructure.persistence.index_reader import SqlAlchemyIndexReader
from backend.infrastructure.persistence.medicine_reader import SqlAlchemyMedicineReader
from backend.infrastructure.persistence.sqlite_engine import create_sqlite_engine
from backend.infrastructure.sources.file_index_source import FileIndexSourceReader
from backend.tests.support.paths import PROJECT_ROOT
from backend.tests.support.storage_fixtures import build_document_store
from sqlalchemy.engine import URL

REPO_ROOT = PROJECT_ROOT
STRUCTURED_DIR = REPO_ROOT / "data" / "pmda" / "structured"


class PackageInsertStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.index_path = self.root / "test_index.sqlite3"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def engine(self):
        build_document_store(STRUCTURED_DIR, self.index_path)
        return create_sqlite_engine(
            URL.create("sqlite", database=self.index_path.as_posix()).render_as_string(
                hide_password=False
            )
        )

    def test_document_reader_preserves_content_and_independent_results(self) -> None:
        engine = self.engine()
        try:
            reader = SqlAlchemyIndexReader(engine)
            stats = asyncio.run(reader.read_index_stats())
            with engine.connect() as connection:
                first_key = connection.exec_driver_sql(
                    "SELECT document_key FROM documents LIMIT 1"
                ).scalar_one()
                count = connection.exec_driver_sql(
                    "SELECT COUNT(*) FROM documents"
                ).scalar_one()
            self.assertEqual(stats["document_count"], count)
            payload = asyncio.run(reader.get_document(first_key))
            assert payload is not None
            document = payload["document"]
            assert isinstance(document, dict)
            self.assertEqual(
                f"{document['company_identifier']}_{document['package_insert_no']}",
                first_key,
            )
            repeated = asyncio.run(reader.get_document(first_key))
            self.assertEqual(payload, repeated)
            document["company_identifier"] = "changed"
            self.assertEqual(asyncio.run(reader.get_document(first_key)), repeated)
            self.assertIsNone(asyncio.run(reader.get_document("missing_key")))
        finally:
            engine.dispose()

    def test_medicines_table_and_indexes_created(self) -> None:
        engine = self.engine()
        try:
            medicines = asyncio.run(SqlAlchemyMedicineReader(engine).read_medicines())
            with engine.connect() as connection:
                count = connection.exec_driver_sql(
                    "SELECT COUNT(*) FROM medicines"
                ).scalar_one()
                self.assertEqual(count, len(medicines))
                self.assertGreater(count, 0)
                names = {
                    row[0]
                    for row in connection.exec_driver_sql(
                        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='medicines'"
                    )
                }
                self.assertIn("idx_medicines_yj", names)
                self.assertIn("idx_medicines_doc", names)
                self.assertEqual(
                    connection.exec_driver_sql("PRAGMA journal_mode")
                    .scalar_one()
                    .lower(),
                    "wal",
                )
        finally:
            engine.dispose()

    def test_medicine_catalog_resolves_yj_code(self) -> None:
        engine = self.engine()
        try:
            medicines = asyncio.run(SqlAlchemyMedicineReader(engine).read_medicines())
            original = FileIndexSourceReader(STRUCTURED_DIR).read_snapshot().medicines
            self.assertTrue(
                all(type(medicine) is RegisteredMedicine for medicine in medicines)
            )
            self.assertEqual(sorted(medicines, key=repr), sorted(original, key=repr))
            catalog = MedicineCatalog(medicines)
            sample_yj = next(
                medicine.yj_code.value for medicine in medicines if medicine.yj_code
            )
            resolved = catalog.match_yj_codes([sample_yj])
            self.assertEqual(len(resolved), 1)
            self.assertIn(sample_yj, resolved[0].yj_codes)
        finally:
            engine.dispose()

    def test_manifest_fingerprint_fast_path(self) -> None:
        structured = self.root / "structured"
        structured.mkdir()
        sample = next(STRUCTURED_DIR.glob("*/document.json")).parent
        shutil.copytree(sample, structured / sample.name)
        fingerprint = FileIndexSourceReader(structured).read_snapshot().fingerprint
        self.assertFalse(fingerprint.startswith("manifest:"))
        (structured / "manifest.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "document_count": 1,
                    "generated_at": "2026-09-27T00:00:00Z",
                    "sha256": "fakehash12345",
                }
            ),
            encoding="utf-8",
        )
        fingerprint = FileIndexSourceReader(structured).read_snapshot().fingerprint
        self.assertTrue(fingerprint.startswith("content-v1:"))
        self.assertEqual(
            fingerprint, FileIndexSourceReader(structured).read_snapshot().fingerprint
        )
        document_path = structured / sample.name / "document.json"
        original_document = document_path.read_bytes()
        document_path.write_bytes(original_document + b" ")
        document_changed = FileIndexSourceReader(structured).read_snapshot().fingerprint
        self.assertNotEqual(fingerprint, document_changed)
        document_path.write_bytes(original_document)
        self.assertEqual(
            fingerprint, FileIndexSourceReader(structured).read_snapshot().fingerprint
        )
        units_path = structured / sample.name / "search_units.jsonl"
        original_units = units_path.read_bytes()
        rows = [
            json.loads(line)
            for line in original_units.decode("utf-8").splitlines()
            if line
        ]
        rows[0]["text"] += "追加本文"
        units_path.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
            encoding="utf-8",
        )
        self.assertNotEqual(
            fingerprint, FileIndexSourceReader(structured).read_snapshot().fingerprint
        )
