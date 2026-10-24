"""Read-only import receipts, history and publication results."""

from dataclasses import replace

from sqlalchemy import func, select, text
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
from backend.infrastructure.index_payloads import (
    result_from_dict,
)

from . import postgres_schema as s


class PostgresImportQueries:
    def __init__(self, engine: Engine):
        self.engine = engine

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

    def replay_result(self, document_id: str, digest: str) -> ImportResult:
        """Replay a retained receipt even after its original payload was reclaimed."""
        return self.result(f"{document_id}:{digest}", reused=True)

    def list_imports(self, *, limit: int, offset: int) -> ImportPage:
        try:
            with self.engine.connect().execution_options(
                isolation_level="REPEATABLE READ"
            ) as connection:
                connection.execute(text("SET TRANSACTION READ ONLY"))
                total = connection.execute(
                    select(func.count()).select_from(s.receipts)
                ).scalar_one()
                records = (
                    connection.execute(
                        select(s.receipts, s.versions.c.filename)
                        .outerjoin(
                            s.versions,
                            s.versions.c.version_id == s.receipts.c.version_id,
                        )
                        .order_by(s.receipts.c.sequence.desc())
                        .limit(limit)
                        .offset(offset)
                    )
                    .mappings()
                    .all()
                )
                active: dict[str, list[str]] = {}
                if records:
                    for row in connection.execute(
                        select(s.active.c.version_id, s.active.c.yj_code)
                        .where(
                            s.active.c.version_id.in_(
                                [r["version_id"] for r in records]
                            )
                        )
                        .order_by(s.active.c.yj_code.collate("C"))
                    ):
                        active.setdefault(row.version_id, []).append(row.yj_code)
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

    def result(
        self, identity: str, *, reused: bool = False, get: bool = False
    ) -> ImportResult:
        with self.engine.connect().execution_options(
            isolation_level="REPEATABLE READ"
        ) as connection:
            connection.execute(text("SET TRANSACTION READ ONLY"))
            record = (
                connection.execute(
                    select(s.receipts).where(s.receipts.c.version_id == identity)
                )
                .mappings()
                .first()
            )
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
            active = tuple(
                sorted(
                    connection.execute(
                        select(s.active.c.yj_code).where(
                            s.active.c.version_id == identity
                        )
                    ).scalars()
                )
            )
            generation = connection.execute(
                select(s.state.c.generation_id)
            ).scalar_one()
            targets = connection.execute(
                select(
                    s.receipts.c.version_id,
                    s.receipts.c.artifacts_deleted,
                    s.receipts.c.cleanup_reason,
                ).where(
                    s.receipts.c.version_id.in_(record["cleanup_targets"]),
                    s.receipts.c.version_id.not_in(select(s.active.c.version_id)),
                )
            ).all()
        pending = tuple(
            (target.version_id, target.cleanup_reason or "cleanup_required")
            for target in sorted(targets)
            if not target.artifacts_deleted
        )
        deleted = tuple(
            target.version_id for target in sorted(targets) if target.artifacts_deleted
        )
        return replace(
            result_from_dict(record["result"]),
            reused=reused,
            status=("registered_cleanup_pending" if pending else "registered")
            if active
            else "superseded",
            search_index_updated=bool(active),
            registration_sequence=record["sequence"],
            active_yj_codes=active,
            generation_id=generation,
            replaced_yj_codes=tuple(record["replaced"]),
            artifacts_deleted=record["artifacts_deleted"],
            deleted_version_ids=deleted,
            cleanup_pending=pending,
        )
