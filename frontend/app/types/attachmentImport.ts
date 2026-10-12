export interface AttachmentImportResult {
  document_id: string;
  source_sha256: string;
  status: string;
  reused: boolean;
  validation_status: string;
  section_count: number;
  search_unit_count: number;
  products: { yj_code: string | null; brand_name: string | null }[];
  revisions: {
    source_label: string | null;
    year_month: string | null;
    version: string | null;
  }[];
  warnings: { code: string; reference: string }[];
  search_index_updated: boolean;
  generation_id: string | null;
  registration_sequence: number | null;
  active_yj_codes: string[];
  replaced_yj_codes: string[];
  deleted_version_ids: string[];
  cleanup_pending: { version_id: string; reason: string }[];
  artifacts_deleted: boolean;
}
