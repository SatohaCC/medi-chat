"""No legacy SQLite migration or compatibility adapters are retained."""

import importlib.util

import pytest


@pytest.mark.parametrize(
    "module",
    [
        "backend.infrastructure.cli.migrate_legacy_index",
        "backend.infrastructure.persistence.legacy_content_validator",
        "backend.infrastructure.persistence.legacy_schema_validator",
        "backend.infrastructure.persistence.legacy_index_backup",
        "backend.infrastructure.persistence.legacy_migration_verifier",
        "backend.migrations.legacy_copy_stamp",
        "backend.infrastructure.persistence.sqlite_engine",
        "backend.infrastructure.persistence.attachment_import_store",
        "backend.infrastructure.persistence.registration_reader",
        "backend.infrastructure.persistence.generation_runtime",
        "backend.infrastructure.cli.build_search_index",
        "backend.infrastructure.cli.initialize_registrations",
    ],
)
def test_old_sqlite_migration_modules_are_removed(module):
    assert importlib.util.find_spec(module) is None
