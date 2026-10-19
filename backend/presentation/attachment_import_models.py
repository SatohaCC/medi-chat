from pydantic import BaseModel

from ..application.attachment_import.import_models import ImportPage, ImportResult


class ImportedProductResponse(BaseModel):
    yj_code: str | None
    brand_name: str | None


class ImportedRevisionResponse(BaseModel):
    source_label: str | None
    year_month: str | None
    version: str | None


class ImportSummaryResponse(BaseModel):
    document_id: str
    source_sha256: str
    filename: str | None
    registration_sequence: int
    revised_at: str
    products: list[ImportedProductResponse]
    active_yj_codes: list[str]
    artifacts_deleted: bool


class ImportListResponse(BaseModel):
    items: list[ImportSummaryResponse]
    total_count: int
    limit: int
    offset: int

    @classmethod
    def from_page(
        cls, page: ImportPage, *, limit: int, offset: int
    ) -> ImportListResponse:
        return cls(
            items=[
                ImportSummaryResponse(
                    document_id=item.document_id,
                    source_sha256=item.source_sha256,
                    filename=item.filename,
                    registration_sequence=item.registration_sequence,
                    revised_at=item.revised_at,
                    products=[
                        ImportedProductResponse(
                            yj_code=p.yj_code, brand_name=p.brand_name
                        )
                        for p in item.products
                    ],
                    active_yj_codes=list(item.active_yj_codes),
                    artifacts_deleted=item.artifacts_deleted,
                )
                for item in page.items
            ],
            total_count=page.total_count,
            limit=limit,
            offset=offset,
        )


class ImportWarningResponse(BaseModel):
    code: str
    reference: str


class ImportErrorDetail(BaseModel):
    code: str
    message: str
    phase: str


class ImportErrorResponse(BaseModel):
    detail: ImportErrorDetail


class ImportConflictItem(BaseModel):
    yj_code: str
    version_ids: list[str]


class ImportConflictDetail(ImportErrorDetail):
    conflicts: list[ImportConflictItem]


class ImportConflictResponse(BaseModel):
    detail: ImportConflictDetail


class AttachmentImportResponse(BaseModel):
    document_id: str
    source_sha256: str
    status: str
    reused: bool
    validation_status: str
    section_count: int
    search_unit_count: int
    products: list[ImportedProductResponse]
    revisions: list[ImportedRevisionResponse]
    warnings: list[ImportWarningResponse]
    search_index_updated: bool
    generation_id: str | None
    registration_sequence: int | None
    active_yj_codes: list[str]
    replaced_yj_codes: list[str]
    deleted_version_ids: list[str]
    cleanup_pending: list[CleanupPendingResponse]
    artifacts_deleted: bool

    @classmethod
    def from_result(cls, result: ImportResult) -> AttachmentImportResponse:
        return cls(
            document_id=result.document_id,
            source_sha256=result.source_sha256,
            status=result.status,
            reused=result.reused,
            validation_status=result.validation_status,
            section_count=result.section_count,
            search_unit_count=result.search_unit_count,
            products=[
                ImportedProductResponse(yj_code=p.yj_code, brand_name=p.brand_name)
                for p in result.products
            ],
            revisions=[
                ImportedRevisionResponse(
                    source_label=r.source_label,
                    year_month=r.year_month,
                    version=r.version,
                )
                for r in result.revisions
            ],
            warnings=[
                ImportWarningResponse(code=w.code, reference=w.reference)
                for w in result.warnings
            ],
            search_index_updated=result.search_index_updated,
            generation_id=result.generation_id,
            registration_sequence=result.registration_sequence,
            active_yj_codes=list(result.active_yj_codes),
            replaced_yj_codes=list(result.replaced_yj_codes),
            deleted_version_ids=list(result.deleted_version_ids),
            cleanup_pending=[
                CleanupPendingResponse(version_id=version, reason=reason)
                for version, reason in result.cleanup_pending
            ],
            artifacts_deleted=result.artifacts_deleted,
        )


class CleanupPendingResponse(BaseModel):
    version_id: str
    reason: str
