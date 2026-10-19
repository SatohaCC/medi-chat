"""Request-owned PostgreSQL MVCC snapshot, materialized before generation."""

from __future__ import annotations

import asyncio
import json
import threading
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass

from sqlalchemy import func, select, text
from sqlalchemy.engine import Connection, Engine

from backend.application.indexing.attachment_projection import project_active_attachment
from backend.application.medicine.product_models import (
    RegisteredMedicine,
    SearchGenerationId,
)
from backend.application.medicine.suggestions import MedicineSuggester
from backend.application.retrieval.snapshot_contracts import RetrievalSnapshot
from backend.domain.foundation.json_types import JsonValue
from backend.domain.medicine.identifiers import YjCode
from backend.domain.retrieval.repositories import EvidenceSearchTarget
from backend.domain.retrieval.value_objects import (
    Evidence,
    SearchCriteria,
    TextSearchPolicy,
)
from backend.domain.shared.services import normalize_match_text, normalize_search_text
from backend.infrastructure.evidence_mapping import (
    build_evidence,
    is_scope_heading_only,
)
from backend.infrastructure.index_payloads import (
    build_index_document,
    build_index_unit,
    encode_registered_units,
    registered_unit_text,
    unit_matches_sections,
)
from backend.infrastructure.package_insert_definitions.loader import (
    get_package_insert_definitions,
)

from . import postgres_schema as s
from .attachment_document_mapping import document_from_payload
from .read_workers import ReadWorkers
from .trigram_search import phrase_scores


@dataclass(frozen=True)
class _SearchRow:
    unit: dict[str, JsonValue]
    catalogue: dict[str, JsonValue]
    raw_json: str
    query_text: str


def _row(unit: dict[str, JsonValue], catalogue: dict[str, JsonValue]) -> _SearchRow:
    indexed = build_index_unit(unit, str(unit["document_key"]))
    return _SearchRow(
        unit, catalogue, json.dumps(unit, ensure_ascii=False), indexed.query_text
    )


async def _owned[T](workers: ReadWorkers, operation: Callable[[], T]) -> T:
    """Cancellation never returns a connection while its native worker is active."""
    task = asyncio.create_task(workers.run(operation))
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
    result = task.result()
    if cancelled:
        raise asyncio.CancelledError()
    return result


class _Scope:
    def __init__(self, runtime: PostgresRuntime) -> None:
        self.runtime = runtime
        self.connection: Connection | None = None
        self.lock = threading.Lock()
        self.closed = False
        self.memberships: dict[str, set[YjCode]] = {}
        self.medicines: tuple[RegisteredMedicine, ...] | None = None
        self.rows: dict[tuple[frozenset[str], frozenset[YjCode]], list[_SearchRow]] = {}
        self.document_count = 0
        self.unit_count = 0

    def open(self) -> None:
        with self.lock:
            connection = self.runtime.engine.connect().execution_options(
                isolation_level="REPEATABLE READ"
            )
            self.connection = connection
            self.runtime.fault("opened")
            connection.execute(text("SET TRANSACTION READ ONLY"))
            generation = connection.execute(
                select(s.state.c.generation_id)
            ).scalar_one()
            if generation is None:
                raise RuntimeError("initial_registration_required")
            self.generation_id = SearchGenerationId(generation)
            self.runtime.fault("pointer")
            for row in connection.execute(
                select(s.memberships.c.version_id, s.memberships.c.yj_code)
                .where(s.memberships.c.generation_id == generation)
                .order_by(
                    s.memberships.c.version_id.collate("C"),
                    s.memberships.c.yj_code.collate("C"),
                )
            ):
                self.memberships.setdefault(row.version_id, set()).add(
                    YjCode(row.yj_code)
                )
            self.document_count = connection.execute(
                select(func.count(func.distinct(s.receipts.c.document_id))).where(
                    s.receipts.c.version_id.in_(self.memberships)
                )
            ).scalar_one()
            scoped_units = (
                select(s.unit_products.c.version_id, s.unit_products.c.section_code)
                .join(
                    s.memberships,
                    (s.memberships.c.version_id == s.unit_products.c.version_id)
                    & (s.memberships.c.yj_code == s.unit_products.c.yj_code),
                )
                .where(s.memberships.c.generation_id == generation)
                .distinct()
                .subquery()
            )
            self.unit_count = connection.execute(
                select(func.count()).select_from(scoped_units)
            ).scalar_one()

    def close(self) -> None:
        with self.lock:
            self.closed = True
            self.rows.clear()
            self.medicines = None
            connection, self.connection = self.connection, None
            if connection is not None:
                connection.close()

    def _live_connection(self) -> Connection:
        if self.closed or self.connection is None:
            raise RuntimeError("Generation snapshot has been released")
        return self.connection

    async def read_medicines(self) -> tuple[RegisteredMedicine, ...]:
        return await _owned(self.runtime.workers, self._read_medicines)

    def _read_medicines(self) -> tuple[RegisteredMedicine, ...]:
        with self.lock:
            connection = self._live_connection()
            self.runtime.fault("medicines")
            if self.medicines is None:
                products: list[RegisteredMedicine] = []
                for row in connection.execute(
                    select(s.versions.c.version_id, s.versions.c.catalogue)
                    .where(s.versions.c.version_id.in_(self.memberships))
                    .order_by(s.versions.c.version_id.collate("C"))
                ):
                    _, medicines = build_index_document(row.catalogue)
                    products.extend(
                        medicine
                        for medicine in medicines
                        if medicine.yj_code in self.memberships[row.version_id]
                    )
                self.medicines = tuple(products)
            return self.medicines

    async def search(
        self, criteria: SearchCriteria, medicines: tuple[EvidenceSearchTarget, ...]
    ) -> tuple[Evidence, ...]:
        return await _owned(
            self.runtime.workers, lambda: self._search(criteria, medicines)
        )

    def _search(
        self, criteria: SearchCriteria, medicines: tuple[EvidenceSearchTarget, ...]
    ) -> tuple[Evidence, ...]:
        with self.lock:
            self._live_connection()
            self.runtime.fault("search")
            requested = frozenset(
                YjCode(code) for target in medicines for code in target.yj_codes
            )
            if not requested:
                return ()
            document_ids = frozenset(
                key for target in medicines for key in target.document_ids
            )
            key = document_ids, requested
            if key not in self.rows:
                self.rows[key] = self._requested_rows(document_ids, requested)
            rows = self.rows[key]
            sections = tuple(code.value for code in criteria.section_codes)

            def in_sections(index: int) -> bool:
                return unit_matches_sections(rows[index].unit, sections)

            selected = [
                index for index in range(len(rows)) if sections and in_sections(index)
            ]
            for keyword in criteria.keywords:
                normalized = normalize_search_text(keyword.value)
                size = len(normalize_match_text(normalized))
                if size < 2:
                    continue
                if size < 3:
                    matches = [
                        index
                        for index, row in enumerate(rows)
                        if keyword.value in row.raw_json
                    ]
                else:
                    matches = [
                        index
                        for index, _ in phrase_scores(
                            tuple(row.query_text for row in rows), normalized
                        )
                    ]
                selected.extend(index for index in matches if in_sections(index))
            return tuple(
                build_evidence(
                    {
                        **rows[index].unit,
                        "text": registered_unit_text(rows[index].unit),
                    },
                    rows[index].catalogue,
                    criteria.source,
                )
                for index in dict.fromkeys(selected)
            )

    def _requested_rows(
        self, document_ids: frozenset[str], requested: frozenset[YjCode]
    ) -> list[_SearchRow]:
        connection = self._live_connection()
        rows: list[_SearchRow] = []
        statement = (
            select(
                s.versions.c.version_id, s.versions.c.structure, s.versions.c.catalogue
            )
            .join(s.receipts, s.receipts.c.version_id == s.versions.c.version_id)
            .where(s.versions.c.version_id.in_(self.memberships))
            # The former public snapshot used Python's codepoint order. Locale
            # ordering would change both catalogue order and equal BM25 ties.
            .order_by(s.versions.c.version_id.collate("C"))
        )
        if document_ids:
            statement = statement.where(s.receipts.c.document_id.in_(document_ids))
        for row in connection.execute(statement):
            codes = frozenset(self.memberships[row.version_id].intersection(requested))
            if not codes:
                continue
            document = document_from_payload(row.structure)
            content = encode_registered_units(
                document, project_active_attachment(document, codes)
            )
            for line in content.splitlines():
                unit = json.loads(line)
                if not is_scope_heading_only(
                    unit, text_search_policy=self.runtime.policy
                ):
                    rows.append(_row(unit, row.catalogue))
        return rows


class PostgresRuntime:
    def __init__(
        self,
        engine: Engine,
        *,
        workers: ReadWorkers,
        fault: Callable[[str], None] = lambda phase: None,
        text_search_policy: TextSearchPolicy | None = None,
    ) -> None:
        self.engine = engine
        self.workers = workers
        self.fault = fault
        self.policy = (
            text_search_policy
            if text_search_policy is not None
            else get_package_insert_definitions().text_search_policy
        )

    async def catalogue(self) -> MedicineSuggester:
        async with self.acquire() as snapshot:
            products = await snapshot.medicine_reader.read_medicines()
            return MedicineSuggester.from_registered_medicines(
                products, generation_id=snapshot.generation_id
            )

    async def statistics(self) -> dict[str, str | int]:
        async with self.acquire() as snapshot:
            return {
                "generation_id": snapshot.generation_id.value,
                "document_count": snapshot.document_count,
                "unit_count": snapshot.unit_count,
            }

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[RetrievalSnapshot]:
        scope = _Scope(self)
        try:
            await _owned(self.workers, scope.open)
            yield RetrievalSnapshot(
                scope.generation_id,
                scope,
                scope,
                scope.document_count,
                scope.unit_count,
            )
        finally:
            await _owned(self.workers, scope.close)
