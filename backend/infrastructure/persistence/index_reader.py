"""SQLAlchemyによる文書と索引統計の読取り境界。"""

from sqlalchemy import func, select
from sqlalchemy.engine import Engine

from ...domain.json_types import JsonValue
from ..json_payloads import parse_json_object
from . import schema
from .read_workers import ReadWorkers, read_workers_for_engine


class SqlAlchemyIndexReader:
    def __init__(self, engine: Engine, *, workers: ReadWorkers | None = None) -> None:
        self._engine = engine
        self._workers = (
            workers if workers is not None else read_workers_for_engine(engine)
        )

    async def get_document(self, document_id: str) -> dict[str, JsonValue] | None:
        return await self._workers.run(lambda: self._get_document(document_id))

    def _get_document(self, document_id: str) -> dict[str, JsonValue] | None:
        with self._engine.connect() as connection:
            payload = connection.execute(
                select(schema.documents.c.payload_json).where(
                    schema.documents.c.document_key == document_id
                )
            ).scalar_one_or_none()
            return parse_json_object(payload) if payload is not None else None

    async def read_index_stats(self) -> dict[str, int]:
        return await self._workers.run(self._read_index_stats)

    def _read_index_stats(self) -> dict[str, int]:
        with self._engine.connect() as connection:
            document_count = connection.execute(
                select(func.count()).select_from(schema.documents)
            ).scalar_one()
            unit_count = connection.execute(
                select(func.count()).select_from(schema.units)
            ).scalar_one()
            return {"document_count": document_count, "unit_count": unit_count}
