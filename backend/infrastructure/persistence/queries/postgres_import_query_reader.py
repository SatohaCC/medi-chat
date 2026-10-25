"""Read-only import queries adapter for presentation and application query handlers."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from backend.application.attachment_import.commands.models import ImportResult
from backend.application.attachment_import.errors import (
    ImportGone,
    ImportNotFound,
    ImportStorageError,
)
from backend.application.attachment_import.queries.dtos.import_views import (
    ImportDetail,
    ImportPage,
    ImportProductView,
    ImportRevisionView,
    ImportSummary,
    ImportWarningView,
)
from backend.infrastructure.persistence.mappings.import_result_mapping import (
    map_receipt_to_import_result,
)
from backend.infrastructure.persistence.records.postgres_import_receipt_records import (
    fetch_active_yj_codes_by_version,
    fetch_cleanup_targets,
    fetch_generation_id,
    fetch_receipt_by_version,
    fetch_receipt_page,
)


class PostgresImportQueries:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def result(
        self, identity: str, *, reused: bool = False, get: bool = False
    ) -> ImportResult:
        with self.engine.connect().execution_options(
            isolation_level="REPEATABLE READ"
        ) as connection:
            connection.execute(text("SET TRANSACTION READ ONLY"))
            record = fetch_receipt_by_version(connection, identity)
            if record is None:
                raise ImportNotFound(
                    "import_not_found",
                    "Registered import does not exist",
                    phase="publication",
                )
            if get and record["artifacts_deleted"]:
                raise ImportGone(
                    "version_deleted",
                    "Registered version artifacts have been deleted",
                    phase="publication",
                )
            active = fetch_active_yj_codes_by_version(connection, identity)
            generation = fetch_generation_id(connection)
            targets = fetch_cleanup_targets(connection, record["cleanup_targets"])

        return map_receipt_to_import_result(
            record,
            active=active,
            generation=generation,
            targets=targets,
            reused=reused,
        )

    def read_result(self, document_id: str, digest: str) -> ImportDetail:
        stored = self.result(f"{document_id}:{digest}", get=True)
        return ImportDetail(
            document_id=stored.document_id,
            source_sha256=stored.source_sha256,
            validation_status=stored.validation_status,
            section_count=stored.section_count,
            search_unit_count=stored.search_unit_count,
            products=tuple(
                ImportProductView(p.yj_code, p.brand_name) for p in stored.products
            ),
            revisions=tuple(
                ImportRevisionView(r.source_label, r.year_month, r.version)
                for r in stored.revisions
            ),
            warnings=tuple(
                ImportWarningView(w.code, w.reference) for w in stored.warnings
            ),
            transformer_version=stored.transformer_version,
            reused=stored.reused,
            status=stored.status,
            search_index_updated=stored.search_index_updated,
            generation_id=stored.generation_id,
            registration_sequence=stored.registration_sequence,
            active_yj_codes=stored.active_yj_codes,
            replaced_yj_codes=stored.replaced_yj_codes,
            deleted_version_ids=stored.deleted_version_ids,
            cleanup_pending=stored.cleanup_pending,
            artifacts_deleted=stored.artifacts_deleted,
        )

    def list_imports(self, *, limit: int, offset: int) -> ImportPage:
        try:
            with self.engine.connect().execution_options(
                isolation_level="REPEATABLE READ"
            ) as connection:
                connection.execute(text("SET TRANSACTION READ ONLY"))
                total, records, active = fetch_receipt_page(
                    connection, limit=limit, offset=offset
                )
                return ImportPage(
                    items=tuple(
                        ImportSummary(
                            document_id=r["document_id"],
                            source_sha256=r["source_sha256"],
                            filename=r["filename"],
                            registration_sequence=r["sequence"],
                            revised_at=r["revised_at"],
                            products=tuple(
                                ImportProductView(p["yj_code"], p["brand_name"])
                                for p in r["result"]["products"]
                            ),
                            active_yj_codes=tuple(active.get(r["version_id"], ())),
                            artifacts_deleted=r["artifacts_deleted"],
                        )
                        for r in records
                    ),
                    total_count=total,
                )
        except SQLAlchemyError:
            raise ImportStorageError(
                "import_list_unavailable",
                "取り込み一覧を取得できません。",
                phase="publication",
            ) from None
