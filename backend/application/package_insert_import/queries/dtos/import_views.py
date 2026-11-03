"""Read-only import detail and history DTOs, independent of Command results."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ImportWarningView:
    code: str
    reference: str


@dataclass(frozen=True, slots=True)
class ImportProductView:
    yj_code: str | None
    brand_name: str | None


@dataclass(frozen=True, slots=True)
class ImportRevisionView:
    source_label: str | None
    year_month: str | None
    version: str | None


@dataclass(frozen=True, slots=True)
class ImportSummary:
    document_id: str
    source_sha256: str
    filename: str | None
    registration_sequence: int
    revised_at: str
    products: tuple[ImportProductView, ...]
    active_yj_codes: tuple[str, ...]
    artifacts_deleted: bool


@dataclass(frozen=True, slots=True)
class ImportPage:
    items: tuple[ImportSummary, ...]
    total_count: int


@dataclass(frozen=True, slots=True)
class ImportDetail:
    document_id: str
    source_sha256: str
    validation_status: str
    section_count: int
    search_unit_count: int
    products: tuple[ImportProductView, ...]
    revisions: tuple[ImportRevisionView, ...]
    warnings: tuple[ImportWarningView, ...]
    transformer_version: str
    reused: bool = False
    status: str = "stored"
    search_index_updated: bool = False
    generation_id: str | None = None
    registration_sequence: int | None = None
    active_yj_codes: tuple[str, ...] = ()
    replaced_yj_codes: tuple[str, ...] = ()
    deleted_version_ids: tuple[str, ...] = ()
    cleanup_pending: tuple[tuple[str, str], ...] = ()
    artifacts_deleted: bool = False
