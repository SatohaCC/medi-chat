"""SQLAlchemyによる索引書込みの境界。"""

import json

from sqlalchemy import delete, func, insert, select, text
from sqlalchemy.engine import Connection, Engine

from ...application.indexing.index_models import IndexBuildResult, SourceSnapshot
from . import schema


class SqlAlchemyIndexWriter:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def replace(self, snapshot: SourceSnapshot) -> IndexBuildResult:
        with self._engine.begin() as connection:
            exists = connection.execute(
                text("SELECT name FROM sqlite_master WHERE name='registration_state'")
            ).first()
            if (
                exists
                and connection.execute(
                    text("SELECT generation_id FROM registration_state")
                ).first()
            ):
                current = connection.execute(
                    select(schema.index_meta.c.value).where(
                        schema.index_meta.c.key == "source_fingerprint"
                    )
                ).scalar_one_or_none()
                if current != snapshot.fingerprint:
                    raise RuntimeError(
                        "Registered index requires the common registration publisher"
                    )
            return self.replace_in_transaction(connection, snapshot)

    def replace_in_transaction(
        self, connection: Connection, snapshot: SourceSnapshot
    ) -> IndexBuildResult:
        current_fingerprint = connection.execute(
            select(schema.index_meta.c.value).where(
                schema.index_meta.c.key == "source_fingerprint"
            )
        ).scalar_one_or_none()
        if current_fingerprint == snapshot.fingerprint:
            document_count = connection.execute(
                select(func.count()).select_from(schema.documents)
            ).scalar_one()
            unit_count = connection.execute(
                select(func.count()).select_from(schema.units)
            ).scalar_one()
            return IndexBuildResult(document_count, unit_count)
        connection.execute(text("DELETE FROM unit_fts"))
        for table in (schema.units, schema.medicines, schema.documents):
            connection.execute(delete(table))

        if snapshot.documents:
            connection.execute(
                insert(schema.documents),
                [
                    {
                        "document_key": document.document_id,
                        "payload_json": json.dumps(
                            document.payload, ensure_ascii=False
                        ),
                    }
                    for document in snapshot.documents
                ],
            )
        if snapshot.medicines:
            connection.execute(
                insert(schema.medicines),
                [
                    {
                        "document_key": medicine.document_id.value,
                        "yj_code": medicine.yj_code.value
                        if medicine.yj_code is not None
                        else None,
                        "brand_name": medicine.brand_name,
                        "generic_name": medicine.generic_name,
                        "english_name": medicine.english_name,
                        "hiragana_name": medicine.hiragana_name,
                        "pmda_url": medicine.pmda_url.value,
                        "revision_json": json.dumps(
                            medicine.revision.to_dict(), ensure_ascii=False
                        ),
                    }
                    for medicine in snapshot.medicines
                ],
            )
        if snapshot.units:
            connection.execute(
                insert(schema.units),
                [
                    {
                        "unit_id": unit.unit_id,
                        "document_key": unit.document_id,
                        "section_code": unit.section_code,
                        "kind": unit.kind,
                        "payload_json": json.dumps(unit.payload, ensure_ascii=False),
                    }
                    for unit in snapshot.units
                ],
            )
            connection.execute(
                text(
                    "INSERT INTO unit_fts "
                    "(unit_id, document_key, section_code, kind, query_text, drug_name) "
                    "VALUES (:unit_id, :document_key, :section_code, :kind, :query_text, :drug_name)"
                ),
                [
                    {
                        "unit_id": unit.unit_id,
                        "document_key": unit.document_id,
                        "section_code": unit.section_code,
                        "kind": unit.kind,
                        "query_text": unit.query_text,
                        "drug_name": unit.drug_name,
                    }
                    for unit in snapshot.units
                ],
            )
        connection.execute(
            delete(schema.index_meta).where(
                schema.index_meta.c.key == "source_fingerprint"
            )
        )
        connection.execute(
            insert(schema.index_meta),
            {"key": "source_fingerprint", "value": snapshot.fingerprint},
        )
        return IndexBuildResult(len(snapshot.documents), len(snapshot.units))
