"""OS leaseで守った同一世代をmaterializeし、取得終了時に解放する。"""

import asyncio
import json
import os
import sqlite3
import uuid
from contextlib import asynccontextmanager, closing, suppress
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import delete, insert, select

from ...application.indexing.attachment_projection import project_active_attachment
from ...application.indexing.medicine_catalog import get_weighted_aliases
from ...application.medicine.suggestions import MedicineSuggester, SuggestionProduct
from ...application.retrieval.snapshot_contracts import RetrievalSnapshot
from ...domain.attachment.entities import AttachmentDocument, AttachmentProductRecord
from ...domain.foundation.value_objects import ImmutableMapping
from ...domain.json_types import JsonValue
from ...domain.medicine.identifiers import YjCode
from ...domain.retrieval.identifiers import SearchGenerationId
from ...domain.retrieval.repositories import EvidenceSearchTarget
from ...domain.retrieval.value_objects import Evidence, SearchCriteria, TextSearchPolicy
from ...domain.shared.services import normalize_match_text, normalize_search_text
from ..evidence_mapping import build_evidence, is_scope_heading_only
from ..index_payloads import build_index_unit
from ..json_payloads import parse_json_object
from ..package_insert_definitions.loader import get_package_insert_definitions
from ..pmda_xml.decoder import PmdaXmlDecoder
from ..pmda_xml.definition_settings import PmdaXmlSettings
from ..pmda_xml.registration_artifacts import encode_registered_units
from ..sources.registration_source import read_registered_snapshot
from . import registration_schema as schema
from .owned_sqlite import OwnedSqliteConnection
from .process_identity import process_identity
from .read_workers import ReadWorkers
from .registration_publisher import SqliteRegistrationPublisher


@dataclass(frozen=True, slots=True)
class _Document:
    document: AttachmentDocument
    metadata: ImmutableMapping[JsonValue]
    active_codes: frozenset[YjCode]


@dataclass(frozen=True, slots=True)
class _Generation:
    generation_id: SearchGenerationId
    medicines: tuple[AttachmentProductRecord, ...]
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

    def close(self) -> None:
        self._closed = True

    async def read_medicines(self) -> tuple[AttachmentProductRecord, ...]:
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
        requested = {YjCode(code) for target in medicines for code in target.yj_codes}
        if not requested:
            return ()
        document_ids = {key for target in medicines for key in target.document_ids}
        rows: list[tuple[dict[str, JsonValue], dict[str, JsonValue]]] = []
        for entry in self.generation.documents:
            if document_ids and entry.document.document_id.value not in document_ids:
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
            for line in content.decode("utf-8").splitlines():
                unit = parse_json_object(line)
                if not is_scope_heading_only(
                    unit, text_search_policy=self._text_search_policy
                ):
                    rows.append((unit, entry.metadata.to_dict()))
        selected: list[int] = []
        sections = {code.value for code in criteria.section_codes}

        def in_sections(unit: dict[str, JsonValue]) -> bool:
            section = unit.get("section")
            return isinstance(section, dict) and section.get("code") in sections

        if sections:
            selected.extend(
                index for index, (unit, _) in enumerate(rows) if in_sections(unit)
            )
        # Exact trigram MATCH over a private request projection. Configured index
        # schema/current rows are never created or reread here.
        with closing(sqlite3.connect(":memory:")) as connection:
            connection.execute(
                "CREATE VIRTUAL TABLE fts USING fts5(query_text, unit_index UNINDEXED, tokenize='trigram')"
            )
            for index, (unit, _) in enumerate(rows):
                indexed = build_index_unit(unit, str(unit["document_key"]))
                connection.execute(
                    "INSERT INTO fts VALUES (?,?)", (indexed.query_text, index)
                )
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


class GenerationRuntime:
    def __init__(
        self,
        publisher: SqliteRegistrationPublisher,
        *,
        workers: ReadWorkers,
        text_search_policy: TextSearchPolicy | None = None,
        xml_settings: PmdaXmlSettings | None = None,
    ):
        self._xml_settings = (
            xml_settings
            if xml_settings is not None
            else get_package_insert_definitions().xml_settings
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

    def _acquire(self) -> tuple[str, _Generation]:
        engine = self.publisher._engine()
        lease_id = uuid.uuid4().hex
        try:
            with self.publisher._lock(lambda: None):
                source = read_registered_snapshot(self.publisher.index_path)
                if source is None:
                    raise RuntimeError("initial_registration_required")
                with engine.begin() as connection:
                    generation_id = connection.execute(
                        select(schema.registration_state.c.generation_id)
                    ).scalar_one()
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
                    if (
                        self._cache is not None
                        and self._cache.generation_id.value == generation_id
                    ):
                        generation = self._cache
                    else:
                        active: dict[str, set[YjCode]] = {}
                        for code, version in connection.execute(
                            select(
                                schema.active_registrations.c.yj_code,
                                schema.active_registrations.c.version_id,
                            )
                        ):
                            active.setdefault(version, set()).add(YjCode(code))
                        documents = []
                        for version, codes in sorted(active.items()):
                            receipt = (
                                connection.execute(
                                    select(schema.registration_receipts).where(
                                        schema.registration_receipts.c.version_id
                                        == version
                                    )
                                )
                                .mappings()
                                .one()
                            )
                            metadata = connection.execute(
                                select(
                                    schema.registration_version_artifacts.c.document_payload_json
                                ).where(
                                    schema.registration_version_artifacts.c.version_id
                                    == version
                                )
                            ).scalar_one()
                            decoded = PmdaXmlDecoder(
                                xml_settings=self._xml_settings
                            ).decode(Path(receipt["source_path"]).read_bytes())
                            documents.append(
                                _Document(
                                    decoded.document,
                                    ImmutableMapping(parse_json_object(metadata)),
                                    frozenset(codes),
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
                return lease_id, generation
        finally:
            engine.dispose()

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
            engine.dispose()

    async def _finish_release(self, lease_id: str) -> None:
        task = asyncio.create_task(self.workers.run(lambda: self._release(lease_id)))
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
            reader.close()
            await self._finish_release(lease_id)

    async def catalogue(self) -> MedicineSuggester:
        async with self.acquire() as snapshot:
            products = await snapshot.medicine_reader.read_medicines()
            return MedicineSuggester(
                tuple(
                    SuggestionProduct(
                        group_name=product.ingredient_id.value,
                        generic_name=product.generic_name,
                        brand_name=product.brand_name,
                        yj_code=product.yj_code,
                        document_id=product.document_id,
                        aliases=tuple(get_weighted_aliases(product)),
                    )
                    for product in products
                ),
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
