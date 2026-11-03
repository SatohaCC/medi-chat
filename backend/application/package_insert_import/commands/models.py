"""Command results and processing state; never imported by queries."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ImportWarning:
    code: str
    reference: str


@dataclass(frozen=True, slots=True)
class ImportedProduct:
    yj_code: str | None
    brand_name: str | None


@dataclass(frozen=True, slots=True)
class ImportedRevision:
    source_label: str | None
    year_month: str | None
    version: str | None


@dataclass(frozen=True, slots=True)
class ImportResult:
    document_id: str
    source_sha256: str
    validation_status: str
    section_count: int
    search_unit_count: int
    products: tuple[ImportedProduct, ...]
    revisions: tuple[ImportedRevision, ...]
    warnings: tuple[ImportWarning, ...]
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


@dataclass(frozen=True, slots=True)
class UploadImportReceipt:
    document_id: str
    source_sha256: str
