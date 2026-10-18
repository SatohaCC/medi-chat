"""SQLAlchemyによる根拠読取りの境界。"""

from sqlalchemy import Text, column, func, select, table, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.sql.selectable import FromClause, Select

from ...domain.retrieval.primitives import DetectionSource
from ...domain.retrieval.repositories import EvidenceRepository, EvidenceSearchTarget
from ...domain.retrieval.value_objects import Evidence, SearchCriteria, TextSearchPolicy
from ...domain.shared.services import (
    normalize_match_text,
    normalize_search_text,
)
from ..evidence_mapping import build_evidence, is_scope_heading_only
from ..index_payloads import registered_unit_text
from ..json_payloads import parse_json_object
from ..package_insert_definitions.loader import get_package_insert_definitions
from . import registration_schema, schema
from .read_workers import ReadWorkers, read_workers_for_engine

_UNIT_FTS = table(
    "unit_fts",
    column("unit_id", Text),
    column("document_key", Text),
    column("section_code", Text),
)


def _unit_document_select(unit_tables: FromClause) -> Select[str, str | None]:
    return select(
        schema.units.c.payload_json,
        schema.documents.c.payload_json.label("document_payload_json"),
    ).select_from(
        unit_tables.outerjoin(
            schema.documents,
            schema.units.c.document_key == schema.documents.c.document_key,
        )
    )


def _read_evidence(
    connection: Connection,
    statement: Select[str, str | None],
    source: DetectionSource,
    text_search_policy: TextSearchPolicy,
    requested_yj_codes: frozenset[str] = frozenset(),
) -> list[Evidence]:
    evidence: list[Evidence] = []
    for row in connection.execute(statement).mappings():
        unit = parse_json_object(row["payload_json"])
        if (
            unit.get("schema_version") == "medi-chat.pmda-sections.v3"
            and requested_yj_codes
        ):
            codes = unit.get("product_yj_codes")
            if not isinstance(codes, list) or not requested_yj_codes.intersection(
                code for code in codes if isinstance(code, str)
            ):
                continue
        if is_scope_heading_only(unit, text_search_policy=text_search_policy):
            continue
        document = (
            parse_json_object(row["document_payload_json"])
            if row["document_payload_json"] is not None
            else {}
        )
        if unit.get("schema_version") == "medi-chat.pmda-sections.v3":
            payload = connection.execute(
                select(
                    registration_schema.registration_version_artifacts.c.document_payload_json
                ).where(
                    registration_schema.registration_version_artifacts.c.version_id
                    == unit["version_id"]
                )
            ).scalar_one()
            document = parse_json_object(payload)
        evidence.append(
            build_evidence(
                {**unit, "text": registered_unit_text(unit)}, document, source
            )
        )
    return evidence


class SqlAlchemyEvidenceReader(EvidenceRepository):
    def __init__(
        self,
        engine: Engine,
        *,
        text_search_policy: TextSearchPolicy | None = None,
        workers: ReadWorkers | None = None,
    ) -> None:
        self._engine = engine
        self._text_search_policy = (
            text_search_policy
            if text_search_policy is not None
            else get_package_insert_definitions().text_search_policy
        )
        self._workers = (
            workers if workers is not None else read_workers_for_engine(engine)
        )

    async def search(
        self, criteria: SearchCriteria, medicines: tuple[EvidenceSearchTarget, ...]
    ) -> tuple[Evidence, ...]:
        return await self._workers.run(lambda: self._search(criteria, medicines))

    def _search(
        self, criteria: SearchCriteria, medicines: tuple[EvidenceSearchTarget, ...]
    ) -> tuple[Evidence, ...]:
        document_ids = list(
            dict.fromkeys(
                key for medicine in medicines for key in medicine.document_ids
            )
        )
        evidence: list[Evidence] = []
        requested_yj_codes = frozenset(
            code for medicine in medicines for code in medicine.yj_codes
        )
        with self._engine.connect() as connection:
            if criteria.section_codes:
                for start in range(0, len(document_ids), 400):
                    chunk = document_ids[start : start + 400]
                    statement = (
                        _unit_document_select(schema.units)
                        .where(
                            schema.units.c.document_key.in_(chunk),
                            schema.units.c.section_code.in_(
                                tuple(code.value for code in criteria.section_codes)
                            ),
                        )
                        .order_by(
                            schema.units.c.section_code.collate("section_code_order"),
                            schema.units.c.unit_id,
                        )
                    )
                    evidence.extend(
                        _read_evidence(
                            connection,
                            statement,
                            criteria.source,
                            self._text_search_policy,
                            requested_yj_codes,
                        )
                    )
            for keyword in criteria.keywords:
                query = keyword.value
                normalized = normalize_search_text(query)
                alias_length = len(normalize_match_text(normalized))
                if alias_length < 2:
                    continue
                unit_tables: FromClause = schema.units
                document_key_column = schema.units.c.document_key
                section_code_column = schema.units.c.section_code
                if alias_length >= 3:
                    unit_tables = _UNIT_FTS.join(
                        schema.units, _UNIT_FTS.c.unit_id == schema.units.c.unit_id
                    )
                    document_key_column = _UNIT_FTS.c.document_key
                    section_code_column = _UNIT_FTS.c.section_code
                statement = _unit_document_select(unit_tables)
                if alias_length < 3:
                    statement = statement.where(
                        func.instr(schema.units.c.payload_json, query) > 0
                    )
                else:
                    expression = 'query_text : "' + normalized.replace('"', '""') + '"'
                    statement = statement.where(
                        text("unit_fts MATCH :expression").bindparams(
                            expression=expression
                        )
                    ).order_by(text("bm25(unit_fts)"))
                if document_ids:
                    statement = statement.where(document_key_column.in_(document_ids))
                if criteria.section_codes:
                    statement = statement.where(
                        section_code_column.in_(
                            tuple(code.value for code in criteria.section_codes)
                        )
                    )
                evidence.extend(
                    _read_evidence(
                        connection,
                        statement,
                        criteria.source,
                        self._text_search_policy,
                        requested_yj_codes,
                    )
                )
        return tuple(evidence)
