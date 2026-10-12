"""明示migrationでのみ作る登録公開schema。"""

from sqlalchemy import Column, Integer, Table, Text

from .schema import metadata

registration_receipts = Table(
    "registration_receipts",
    metadata,
    Column("version_id", Text, primary_key=True),
    Column("document_id", Text, nullable=False),
    Column("source_sha256", Text, nullable=False),
    Column("sequence", Integer, nullable=False, unique=True),
    Column("yj_codes_json", Text, nullable=False),
    Column("replaced_json", Text, nullable=False),
    Column("result_json", Text, nullable=False),
    Column("source_path", Text, nullable=False),
    Column("files_json", Text, nullable=False),
    Column("cleanup_targets_json", Text, nullable=False),
    Column("artifacts_deleted", Integer, nullable=False),
    Column("cleanup_reason", Text, nullable=False),
)
registration_version_artifacts = Table(
    "registration_version_artifacts",
    metadata,
    Column("version_id", Text, primary_key=True),
    Column("document_payload_json", Text, nullable=False),
)
active_registrations = Table(
    "active_registrations",
    metadata,
    Column("yj_code", Text, primary_key=True),
    Column("version_id", Text, nullable=False),
)
registration_generations = Table(
    "registration_generations",
    metadata,
    Column("generation_id", Text, primary_key=True),
    Column("snapshot_json", Text, nullable=False),
    Column("fingerprint", Text, nullable=False),
    Column("files_json", Text, nullable=False),
)
registration_state = Table(
    "registration_state",
    metadata,
    Column("singleton", Integer, primary_key=True),
    Column("generation_id", Text, nullable=False),
)
generation_leases = Table(
    "generation_leases",
    metadata,
    Column("lease_id", Text, primary_key=True),
    Column("generation_id", Text, nullable=False),
    Column("owner_pid", Integer, nullable=False),
    Column("owner_start", Text, nullable=False),
)
registration_owned_files = Table(
    "registration_owned_files",
    metadata,
    Column("version_id", Text, primary_key=True),
    Column("file_id", Text, primary_key=True),
    Column("root", Text, nullable=False),
    Column("sha256", Text, nullable=False),
)
TABLES = (
    registration_receipts,
    registration_version_artifacts,
    active_registrations,
    registration_generations,
    registration_state,
    generation_leases,
    registration_owned_files,
)
