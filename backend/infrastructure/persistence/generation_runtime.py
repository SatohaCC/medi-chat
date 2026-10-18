"""OS leaseで守った同一世代をmaterializeし、取得終了時に解放する。"""

import asyncio
import json
import os
import sqlite3
import threading
import uuid
from contextlib import asynccontextmanager, closing, suppress
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import delete, insert, select
from sqlalchemy.engine import Connection

from backend.application.medicine.product_models import RegisteredMedicine

from ...application.attachment_import.import_contracts import AttachmentDecoder
from ...application.indexing.attachment_projection import project_active_attachment
from ...application.medicine.suggestions import MedicineSuggester
from ...application.retrieval.snapshot_contracts import (
    RetrievalSnapshot,
    SearchGenerationId,
)
from ...domain.attachment.entities import AttachmentDocument
from ...domain.foundation.json_types import JsonValue
from ...domain.foundation.value_objects import ImmutableMapping
from ...domain.medicine.identifiers import YjCode
from ...domain.retrieval.repositories import EvidenceSearchTarget
from ...domain.retrieval.value_objects import Evidence, SearchCriteria, TextSearchPolicy
from ...domain.shared.services import normalize_match_text, normalize_search_text
from ..evidence_mapping import build_evidence, is_scope_heading_only
from ..index_payloads import (
    build_index_unit,
    encode_registered_units,
    unit_matches_sections,
)
from ..json_payloads import parse_json_object
from ..package_insert_definitions.definition_settings import PmdaXmlSettings
from ..package_insert_definitions.loader import get_package_insert_definitions
from ..pmda_xml.decoder import PmdaXmlDecoder
from . import registration_schema as schema
from .owned_sqlite import OwnedSqliteConnection
from .process_identity import process_identity
from .read_workers import ReadWorkers
from .registration_publisher import SqliteRegistrationPublisher
from .registration_reader import read_registered_snapshot


@dataclass(frozen=True, slots=True)
class _Document:
    document: AttachmentDocument
    metadata: ImmutableMapping[JsonValue]
    active_codes: frozenset[YjCode]
    raw_metadata: dict[str, JsonValue] | None = None


@dataclass(frozen=True, slots=True)
class _Generation:
    generation_id: SearchGenerationId
    medicines: tuple[RegisteredMedicine, ...]
    documents: tuple[_Document, ...]
    document_count: int
    unit_count: int


class _SnapshotReader:
    def __init__(
        self,
        generation: _Generation,
        workers: ReadWorkers,
        text_search_policy: TextSearchPolicy,
    ):
        self._text_search_policy = text_search_policy
        self.generation = generation
        self.workers = workers
        self._closed = False
        self._search_lock = threading.Lock()
        self._rows_cache: dict[
            tuple[frozenset[str], frozenset[YjCode]],
            list[tuple[dict[str, JsonValue], dict[str, JsonValue]]],
        ] = {}
        self._fts_cache: dict[
            tuple[frozenset[str], frozenset[YjCode]], sqlite3.Connection
        ] = {}

    def close(self) -> None:
        with self._search_lock:
            self._closed = True
            for connection in self._fts_cache.values():
                connection.close()
            self._fts_cache.clear()
            self._rows_cache.clear()

    async def read_medicines(self) -> tuple[RegisteredMedicine, ...]:
        if self._closed:
            raise RuntimeError("Generation snapshot has been released")
        return self.generation.medicines

    async def search(
        self, criteria: SearchCriteria, medicines: tuple[EvidenceSearchTarget, ...]
    ) -> tuple[Evidence, ...]:
        if self._closed:
            raise RuntimeError("Generation snapshot has been released")
        return await self.workers.run(lambda: self._search(criteria, medicines))

    def _search(
        self, criteria: SearchCriteria, medicines: tuple[EvidenceSearchTarget, ...]
    ) -> tuple[Evidence, ...]:
        # A snapshot can be searched by different worker threads. Serialize access
        # to its private SQLite connections and wait for searches before closing.
        with self._search_lock:
            if self._closed:
                raise RuntimeError("Generation snapshot has been released")
            return self._search_locked(criteria, medicines)

    def _search_locked(
        self, criteria: SearchCriteria, medicines: tuple[EvidenceSearchTarget, ...]
    ) -> tuple[Evidence, ...]:
        requested = {YjCode(code) for target in medicines for code in target.yj_codes}
        if not requested:
            return ()
        document_ids = {key for target in medicines for key in target.document_ids}
        cache_key = (frozenset(document_ids), frozenset(requested))
        if cache_key in self._rows_cache:
            rows = self._rows_cache[cache_key]
        else:
            rows = []
            for entry in self.generation.documents:
                if (
                    document_ids
                    and entry.document.document_id.value not in document_ids
                ):
                    continue
                codes = (
                    entry.active_codes.intersection(requested)
                    if requested
                    else entry.active_codes
                )
                if not codes:
                    continue
                content = encode_registered_units(
                    entry.document,
                    project_active_attachment(entry.document, frozenset(codes)),
                )
                meta_dict = (
                    entry.raw_metadata
                    if entry.raw_metadata is not None
                    else entry.metadata.to_dict()
                )
                for line in content.decode("utf-8").splitlines():
                    unit = parse_json_object(line)
                    if not is_scope_heading_only(
                        unit, text_search_policy=self._text_search_policy
                    ):
                        rows.append((unit, meta_dict))
            self._rows_cache[cache_key] = rows
        selected: list[int] = []
        sections = {code.value for code in criteria.section_codes}

        def in_sections(unit: dict[str, JsonValue]) -> bool:
            return unit_matches_sections(unit, tuple(sections))

        if sections:
            selected.extend(
                index for index, (unit, _) in enumerate(rows) if in_sections(unit)
            )
        # Exact trigram MATCH over a private request projection. Configured index
        # schema/current rows are never created or reread here.
        if criteria.keywords:
            if cache_key not in self._fts_cache:
                connection = sqlite3.connect(":memory:", check_same_thread=False)
                try:
                    self._build_fts(connection, rows)
                except BaseException:
                    connection.close()
                    raise
                self._fts_cache[cache_key] = connection
            connection = self._fts_cache[cache_key]
            for keyword in criteria.keywords:
                normalized = normalize_search_text(keyword.value)
                size = len(normalize_match_text(normalized))
                if size < 2:
                    continue
                if size < 3:
                    matches = [
                        index
                        for index, (unit, _) in enumerate(rows)
                        if keyword.value in json.dumps(unit, ensure_ascii=False)
                    ]
                else:
                    expression = 'query_text : "' + normalized.replace('"', '""') + '"'
                    matches = [
                        int(row[0])
                        for row in connection.execute(
                            "SELECT unit_index FROM fts WHERE fts MATCH ? ORDER BY bm25(fts)",
                            (expression,),
                        )
                    ]
                selected.extend(
                    index
                    for index in matches
                    if not sections or in_sections(rows[index][0])
                )
        return tuple(
            build_evidence(rows[index][0], rows[index][1], criteria.source)
            for index in dict.fromkeys(selected)
        )

    @staticmethod
    def _build_fts(
        connection: sqlite3.Connection,
        rows: list[tuple[dict[str, JsonValue], dict[str, JsonValue]]],
    ) -> None:
        connection.execute(
            "CREATE VIRTUAL TABLE fts USING fts5(query_text, unit_index UNINDEXED, tokenize='trigram')"
        )
        for index, (unit, _) in enumerate(rows):
            indexed = build_index_unit(unit, str(unit["document_key"]))
            connection.execute(
                "INSERT INTO fts VALUES (?,?)", (indexed.query_text, index)
            )


class GenerationRuntime:
    def __init__(
        self,
        publisher: SqliteRegistrationPublisher,
        *,
        workers: ReadWorkers,
        text_search_policy: TextSearchPolicy | None = None,
        xml_settings: PmdaXmlSettings | None = None,
        decoder: AttachmentDecoder | None = None,
    ):
        self._decoder = decoder
        self._xml_settings = (
            xml_settings
            if xml_settings is not None
            else (
                get_package_insert_definitions().xml_settings
                if decoder is None
                else None
            )
        )
        self._text_search_policy = (
            text_search_policy
            if text_search_policy is not None
            else get_package_insert_definitions().text_search_policy
        )
        self.publisher = publisher
        self.workers = workers
        self._cache: _Generation | None = None

    @property
    def cached_generation_id(self) -> SearchGenerationId | None:
        return self._cache.generation_id if self._cache is not None else None

    def _read_generation(
        self, connection: Connection, generation_id: str
    ) -> _Generation:
        if self._cache is not None and self._cache.generation_id.value == generation_id:
            generation = self._cache
        else:
            source = read_registered_snapshot(self.publisher.index_path)
            if source is None:
                raise RuntimeError("initial_registration_required")
            active: dict[str, set[YjCode]] = {}
            for code, version in connection.execute(
                select(
                    schema.active_registrations.c.yj_code,
                    schema.active_registrations.c.version_id,
                )
            ):
                active.setdefault(version, set()).add(YjCode(code))
            documents = []
            decoder = (
                self._decoder
                if self._decoder is not None
                else PmdaXmlDecoder(xml_settings=self._xml_settings)
            )
            for version, codes in sorted(active.items()):
                receipt = (
                    connection.execute(
                        select(schema.registration_receipts).where(
                            schema.registration_receipts.c.version_id == version
                        )
                    )
                    .mappings()
                    .one()
                )
                metadata = connection.execute(
                    select(
                        schema.registration_version_artifacts.c.document_payload_json
                    ).where(
                        schema.registration_version_artifacts.c.version_id == version
                    )
                ).scalar_one()
                decoded = decoder.decode(
                    Path(receipt["source_path"]).read_bytes(),
                    original_filename="source.xml",
                )
                raw_meta = parse_json_object(metadata)
                documents.append(
                    _Document(
                        decoded.document,
                        ImmutableMapping(raw_meta),
                        frozenset(codes),
                        raw_meta,
                    )
                )
            generation = _Generation(
                SearchGenerationId(generation_id),
                source.medicines,
                tuple(documents),
                len(source.documents),
                len(source.units),
            )
            self._cache = generation
        return generation

    def _warmup(self) -> None:
        engine = self.publisher._engine()
        try:
            with self.publisher._lock(lambda: None), engine.connect() as connection:
                generation_id = connection.execute(
                    select(schema.registration_state.c.generation_id)
                ).scalar_one()
                self._read_generation(connection, generation_id)
        finally:
            self.publisher._dispose_engine(engine)

    async def warmup(self) -> None:
        """Materialize the current generation without registering a reader lease."""
        await self.workers.run(self._warmup)

    def _acquire(self) -> tuple[str, _Generation]:
        engine = self.publisher._engine()
        lease_id = uuid.uuid4().hex
        try:
            with self.publisher._lock(lambda: None):
                with engine.begin() as connection:
                    generation_id = connection.execute(
                        select(schema.registration_state.c.generation_id)
                    ).scalar_one_or_none()
                    if generation_id is None:
                        raise RuntimeError("initial_registration_required")
                    start = process_identity(os.getpid())
                    if start is None:
                        raise RuntimeError("Reader owner process is not live")
                    connection.execute(
                        insert(schema.generation_leases),
                        {
                            "lease_id": lease_id,
                            "generation_id": generation_id,
                            "owner_pid": os.getpid(),
                            "owner_start": start,
                        },
                    )
                    generation = self._read_generation(connection, generation_id)
                return lease_id, generation
        finally:
            self.publisher._dispose_engine(engine)

    def _release(self, lease_id: str) -> None:
        engine = self.publisher._engine()
        try:
            with self.publisher._lock(lambda: None):
                with engine.begin() as connection:
                    connection.execute(
                        delete(schema.generation_leases).where(
                            schema.generation_leases.c.lease_id == lease_id
                        )
                    )
                    current = connection.execute(
                        select(schema.registration_state.c.generation_id)
                    ).scalar_one()
                    if (
                        self._cache is not None
                        and self._cache.generation_id.value != current
                    ):
                        self._cache = None
                self.publisher._cleanup(engine)
        finally:
            self.publisher._dispose_engine(engine)

    async def _finish_release(
        self, lease_id: str, reader: _SnapshotReader | None = None
    ) -> None:
        def release() -> None:
            if reader is not None:
                reader.close()
            self._release(lease_id)

        task = asyncio.create_task(self.workers.run(release))
        cancelled = False
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                cancelled = True
        task.result()
        if cancelled:
            raise asyncio.CancelledError()

    @asynccontextmanager
    async def acquire(self):
        acquisition = asyncio.create_task(self.workers.run(self._acquire))
        try:
            lease_id, generation = await asyncio.shield(acquisition)
        except asyncio.CancelledError:
            while not acquisition.done():
                with suppress(asyncio.CancelledError):
                    await asyncio.shield(acquisition)
            lease_id, _ = acquisition.result()
            await self._finish_release(lease_id)
            raise
        reader = _SnapshotReader(generation, self.workers, self._text_search_policy)
        try:
            yield RetrievalSnapshot(
                generation.generation_id,
                reader,
                reader,
                generation.document_count,
                generation.unit_count,
            )
        finally:
            await self._finish_release(lease_id, reader)

    async def catalogue(self) -> MedicineSuggester:
        async with self.acquire() as snapshot:
            products = await snapshot.medicine_reader.read_medicines()
            return MedicineSuggester.from_registered_medicines(
                products,
                generation_id=snapshot.generation_id,
            )

    async def statistics(self) -> dict[str, str | int]:
        def read() -> dict[str, str | int]:
            with self.publisher._lock(lambda: None):
                snapshot = read_registered_snapshot(self.publisher.index_path)
                if snapshot is None:
                    raise RuntimeError("initial_registration_required")
                with closing(
                    sqlite3.connect(
                        self.publisher.index_path.as_uri() + "?mode=ro",
                        uri=True,
                        factory=OwnedSqliteConnection,
                    )
                ) as connection:
                    generation = connection.execute(
                        "SELECT generation_id FROM registration_state WHERE singleton=1"
                    ).fetchone()[0]
                return {
                    "generation_id": generation,
                    "document_count": len(snapshot.documents),
                    "unit_count": len(snapshot.units),
                }

        return await self.workers.run(read)
