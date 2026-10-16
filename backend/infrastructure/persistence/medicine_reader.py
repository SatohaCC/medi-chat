"""SQLAlchemyによる薬剤読取りの境界。"""

from sqlalchemy import select
from sqlalchemy.engine import Engine

from backend.application.medicine.product_contracts import RegisteredMedicineReader
from backend.application.medicine.product_models import RegisteredMedicine
from backend.domain.attachment.value_objects import MedicineDocumentReference
from backend.domain.medicine.entities import MedicineProduct

from ...domain.attachment.identifiers import DocumentId
from ...domain.attachment.primitives import PmdaUrl
from ...domain.attachment.value_objects import AttachmentProductRevision
from ...domain.medicine.identifiers import YjCode
from ..json_payloads import parse_json_object
from . import schema
from .read_workers import ReadWorkers, read_workers_for_engine


class SqlAlchemyMedicineReader(RegisteredMedicineReader):
    def __init__(self, engine: Engine, *, workers: ReadWorkers | None = None) -> None:
        self._engine = engine
        self._workers = (
            workers if workers is not None else read_workers_for_engine(engine)
        )

    async def read_medicines(self) -> tuple[RegisteredMedicine, ...]:
        return await self._workers.run(self._read_medicines)

    def _read_medicines(self) -> tuple[RegisteredMedicine, ...]:
        with self._engine.connect() as connection:
            rows = connection.execute(select(schema.medicines)).mappings()
            return tuple(
                RegisteredMedicine(
                    medicine=MedicineProduct(
                        yj_code=YjCode(row["yj_code"])
                        if row["yj_code"] is not None
                        else None,
                        brand_name=row["brand_name"],
                        generic_name=row["generic_name"],
                        english_name=row["english_name"],
                        hiragana_name=row["hiragana_name"],
                    ),
                    reference=MedicineDocumentReference(
                        document_id=DocumentId(row["document_key"]),
                        pmda_url=PmdaUrl(row["pmda_url"]),
                        revision=AttachmentProductRevision(
                            parse_json_object(row["revision_json"])
                        ),
                    ),
                )
                for row in rows
            )
