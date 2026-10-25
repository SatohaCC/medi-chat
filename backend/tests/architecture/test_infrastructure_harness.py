"""Infrastructure harness test suite.

Verifies static infrastructure boundary enforcement:
- Synthetic positive and forbidden fixtures for layout, naming, imports, onion,
  adapter dependencies, persistence roles, public symbols/consumers, cycles,
  dynamic bypasses, and Repository/ORM/Core responsibilities.
- Inspected source is parsed with AST, never imported or executed.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.checks.infrastructure_architecture import check, main

VALID_CONFIG_TOML = """
[adapters.persistence]
roles = ["schemas", "stores", "queries", "registration", "records", "mappings", "runtime", "maintenance"]
allowed_dependencies = ["serialization", "document_import"]

[adapters.persistence.public]
"stores/postgres_authentication_store" = { symbols = ["PostgresAuthentication"], consumers = ["composition", "cli"] }
"stores/postgres_upload_store" = { symbols = ["PostgresUploadStore", "PostgresUploadImportReceipts"], consumers = ["composition", "cli"] }
"queries/postgres_import_query_reader" = { symbols = ["PostgresImportQueries"], consumers = ["composition", "cli"] }
"queries/postgres_search_snapshot_provider" = { symbols = ["PostgresRuntime"], consumers = ["composition", "cli"] }
"registration/postgres_registration_publisher" = { symbols = ["PostgresRegistrationPublisher"], consumers = ["composition", "cli"] }
"registration/postgres_import_replay_reader" = { symbols = ["PostgresImportReplayReader"], consumers = ["composition", "cli", "persistence.registration"] }
"runtime/postgres_engine" = { symbols = ["create_postgres_engine"], consumers = ["composition", "cli", "backend/migrations/postgres/env.py"] }
"runtime/read_workers" = { symbols = ["ReadWorkers"], consumers = ["composition", "cli"] }
"runtime/import_workers" = { symbols = ["ImportWorkers"], consumers = ["composition", "cli"] }
"runtime/postgres_readiness" = { symbols = ["verify_postgres_readiness"], consumers = ["composition", "cli"] }
"maintenance/postgres_registration_cleanup" = { symbols = ["PostgresRegistrationCleanup"], consumers = ["composition", "cli", "persistence.registration"] }
"schemas/metadata" = { symbols = ["metadata"], consumers = ["backend/migrations", "cli/manage_postgres", "persistence"] }
"schemas/attachment_tables" = { symbols = ["uploads", "upload_parts", "receipts", "versions", "assets", "units", "unit_products", "active", "generations", "memberships", "state"], consumers = ["backend/migrations", "cli/manage_postgres", "persistence"] }
"schemas/authentication_tables" = { symbols = ["users", "identities", "credentials", "families", "refresh_tokens", "attempts", "AUTH_TABLES"], consumers = ["backend/migrations", "cli/manage_postgres", "persistence"] }
"runtime/postgres_integrity" = { symbols = ["PROJECTION_FINGERPRINT"], consumers = ["backend/migrations", "cli/manage_postgres", "persistence.runtime.postgres_readiness"] }
"registration/registration_payloads" = { symbols = ["FigureInput", "PostgresRegistrationInput"], consumers = ["cli/manage_postgres"] }
"mappings/attachment_document_mapping" = { symbols = ["document_from_payload"], consumers = ["cli/manage_postgres"] }
"mappings/search_projection_mapping" = { symbols = ["projection_records"], consumers = ["cli/manage_postgres"] }

[adapters.document_import]
roles = ["attachment_payloads", "attachment_contracts", "original_document_registration_adapter"]
allowed_dependencies = []

[adapters.document_import.public]
"attachment_payloads" = { symbols = ["AttachmentSourceInformation", "DecodedAttachment", "ArtifactFile", "ArtifactBundle"], consumers = ["pmda_xml", "persistence", "composition", "cli"] }
"attachment_contracts" = { symbols = ["AttachmentDecoder", "AttachmentArtifactEncoder", "AttachmentRegistrationPublisher"], consumers = ["pmda_xml", "persistence", "composition", "cli"] }
"original_document_registration_adapter" = { symbols = ["OriginalDocumentRegistration"], consumers = ["composition", "cli"] }

[adapters.serialization]
roles = ["import_result_codec", "search_payload_codec", "search_text_renderer", "evidence_mapping", "json_payload_values"]
allowed_dependencies = []

[adapters.serialization.public]
"import_result_codec" = { symbols = ["result_dict", "result_from_dict"], consumers = ["persistence", "pmda_xml", "cli"] }
"search_payload_codec" = { symbols = ["MAX_ARTIFACT_BYTES", "SEARCH_SCHEMA_VERSION", "DOCUMENT_SCHEMA_VERSION", "json_bytes", "registered_unit_text", "unit_matches_sections", "encode_registered_units", "build_index_unit", "build_index_document"], consumers = ["persistence", "pmda_xml", "cli", "frontend/scripts"] }
"evidence_mapping" = { symbols = ["build_evidence", "is_scope_heading_only"], consumers = ["persistence", "cli", "frontend/scripts"] }

[adapters.llm]
roles = ["llm_provider_base", "llm_provider_factory", "openai_provider", "gemini_provider", "fallback_provider", "mock_response_stream", "llm_provider_errors", "llm_error_messages"]
allowed_dependencies = []

[adapters.llm.public]
"llm_provider_factory" = { symbols = ["create_llm_provider"], consumers = ["composition", "cli"] }

[adapters.intent]
roles = ["jev_classifier", "jev_intent_mapping"]
allowed_dependencies = ["package_insert_definitions"]

[adapters.intent.public]
"jev_classifier" = { symbols = ["JevIntentClassifier"], consumers = ["composition", "backend.main"] }

[adapters.morphology]
roles = ["janome_keyword_extractor", "janome_keyword_extraction"]
allowed_dependencies = ["package_insert_definitions"]

[adapters.morphology.public]
"janome_keyword_extractor" = { symbols = ["JanomeKeywordExtractor"], consumers = ["composition", "backend.main"] }
"janome_keyword_extraction" = { symbols = ["get_janome_tokenizer", "extract_search_keywords"], consumers = ["composition", "backend.main"] }

[adapters.pmda_xml]
roles = ["pmda_xml_decoder", "pmda_artifact_encoder", "xml_safe_parser", "section_mapping", "xml_file_transformer", "search_unit_mapping", "xml_node_mapping", "artifact_builder"]
allowed_dependencies = ["document_import", "serialization", "package_insert_definitions"]

[adapters.pmda_xml.public]
"pmda_xml_decoder" = { symbols = ["PmdaXmlDecoder"], consumers = ["composition", "cli"] }
"pmda_artifact_encoder" = { symbols = ["PmdaArtifactEncoder"], consumers = ["composition", "cli"] }
"xml_file_transformer" = { symbols = ["transform"], consumers = ["composition", "cli"] }
"xml_safe_parser" = { symbols = ["parse_source"], consumers = ["cli/manage_postgres"] }

[adapters.sources]
roles = ["yj_csv_reader"]
allowed_dependencies = []

[adapters.sources.public]
"yj_csv_reader" = { symbols = ["project_yj_row", "parse_yj_csv"], consumers = ["cli"] }

[adapters.authentication]
roles = ["local_credentials", "access_refresh_tokens"]
allowed_dependencies = []

[adapters.authentication.public]
"local_credentials" = { symbols = ["LocalCredentials"], consumers = ["composition", "cli"] }
"access_refresh_tokens" = { symbols = ["JwtTokens", "RefreshSecrets"], consumers = ["composition", "cli"] }

[adapters.package_insert_definitions]
roles = ["definition_assembly", "definition_settings", "jev_settings", "xml_settings"]
allowed_dependencies = []

[adapters.package_insert_definitions.public]
"definition_assembly" = { symbols = ["PackageInsertDefinitions", "build_package_insert_definitions", "get_package_insert_definitions"], consumers = ["composition", "cli", "backend.main", "persistence", "pmda_xml", "intent", "morphology"] }
"definition_settings" = { symbols = ["JevClassificationSettings", "JanomeMorphologySettings", "XmlSectionBinding", "XmlColumnBinding", "PmdaXmlSettings"], consumers = ["composition", "cli", "backend.main", "persistence", "pmda_xml", "intent", "morphology"] }

[adapters.composition]
roles = ["app_lifespan", "authentication_composition"]
allowed_dependencies = ["authentication", "cli", "document_import", "intent", "llm", "morphology", "package_insert_definitions", "persistence", "pmda_xml", "serialization", "sources"]

[adapters.composition.public]
"app_lifespan" = { symbols = ["create_app_lifespan"], consumers = ["backend.main"] }

[adapters.cli]
roles = ["authentication", "build_autocomplete_index", "configured_e2e_gate", "export_search_guide", "manage_postgres", "structure_pmda_xml", "configured_probe"]
allowed_dependencies = ["composition", "authentication", "document_import", "intent", "llm", "morphology", "package_insert_definitions", "persistence", "pmda_xml", "serialization", "sources"]

[adapters.cli.public]
"authentication" = { symbols = ["main"], consumers = [] }
"build_autocomplete_index" = { symbols = ["main"], consumers = [] }
"configured_e2e_gate" = { symbols = ["main"], consumers = [] }
"export_search_guide" = { symbols = ["main"], consumers = [] }
"manage_postgres" = { symbols = ["main"], consumers = [] }
"structure_pmda_xml" = { symbols = ["main"], consumers = [] }
"configured_probe" = { symbols = ["probe_factory"], consumers = [] }
"""


def setup_tree(
    root: Path, files: dict[str, str], toml_config: str = VALID_CONFIG_TOML
) -> Path:
    config_path = root / "backend" / "infrastructure-architecture.toml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(toml_config, encoding="utf-8")
    for relative_path, content in files.items():
        file_path = root / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
    return config_path


# --- IH-001: New declared subject and adapter ---
def test_declared_new_subject_and_adapter(tmp_path: Path) -> None:
    files = {
        "backend/infrastructure/__init__.py": '"""Infrastructure root."""\n',
        "backend/infrastructure/persistence/__init__.py": '"""Persistence package."""\n',
        "backend/infrastructure/persistence/stores/__init__.py": '"""Stores."""\n',
        "backend/infrastructure/persistence/stores/postgres_inventory_store.py": (
            '"""Inventory store."""\n\nclass PostgresInventoryStore:\n    pass\n'
        ),
    }
    setup_tree(tmp_path, files)
    findings = check(tmp_path)
    assert findings == []


# --- IH-002: Layout and role patterns (INF001) ---
def test_layout_and_role_patterns(tmp_path: Path) -> None:
    forbidden_files = [
        (
            "backend/infrastructure/new_adapter/new_reader.py",
            "Undeclared adapter package",
        ),
        ("backend/infrastructure/misc.py", "Direct file under infrastructure root"),
        (
            "backend/infrastructure/persistence/deep/nested/thing.py",
            "Deep arbitrary directory",
        ),
        (
            "backend/infrastructure/persistence/queries/helpers.py",
            "Generic helper name",
        ),
        (
            "backend/infrastructure/persistence/stores/BadName.py",
            "Non-snake_case naming",
        ),
        (
            "backend/infrastructure/persistence/queries/postgres_order_store.py",
            "Role pattern mismatch",
        ),
    ]
    for path, desc in forbidden_files:
        root = tmp_path / path.replace("/", "_")
        files = {
            "backend/infrastructure/__init__.py": '"""Root."""\n',
            path: '"""Module."""\n\ndef run():\n    pass\n',
        }
        setup_tree(root, files)
        findings = check(root)
        rules = [f.rule for f in findings]
        assert "INF001" in rules, f"Expected INF001 for {desc} ({path}), got {findings}"


# --- IH-003: Syntax error is a finding (INF000) ---
def test_syntax_error_is_a_finding(tmp_path: Path) -> None:
    files = {
        "backend/infrastructure/__init__.py": '"""Root."""\n',
        "backend/infrastructure/persistence/__init__.py": '"""Persistence."""\n',
        "backend/infrastructure/persistence/stores/__init__.py": '"""Stores."""\n',
        "backend/infrastructure/persistence/stores/postgres_user_store.py": "def broken(:\n    pass\n",
    }
    config = setup_tree(tmp_path, files)
    findings = check(tmp_path, config=config)
    assert any(f.rule == "INF000" and f.line == 1 for f in findings)

    # CLI exit code should be 1
    code = main(["--root", str(tmp_path), "--config", str(config)])
    assert code == 1


# --- IH-004: Invalid configuration and inputs (exit code 2) ---
def test_invalid_configuration_and_inputs(tmp_path: Path) -> None:
    # 1. Non-existent root
    assert main(["--root", str(tmp_path / "nonexistent")]) == 2

    # 2. Malformed TOML
    cfg = tmp_path / "broken.toml"
    cfg.write_text("broken = [toml", encoding="utf-8")
    assert main(["--root", str(tmp_path), "--config", str(cfg)]) == 2

    # 3. Unknown role or invalid schema
    cfg2 = tmp_path / "unknown_dep.toml"
    cfg2.write_text(
        """
[adapters.persistence]
roles = ["unknown_role"]
allowed_dependencies = ["nonexistent_adapter"]
""",
        encoding="utf-8",
    )
    assert main(["--root", str(tmp_path), "--config", str(cfg2)]) == 2


# --- IH-005: Relative imports (INF002) ---
def test_relative_imports(tmp_path: Path) -> None:
    for rel_import in [
        "from .local import Local",
        "from ..runtime import Engine",
        "from . import something",
    ]:
        root = tmp_path / f"rel_{hash(rel_import)}"
        files = {
            "backend/infrastructure/__init__.py": '"""Root."""\n',
            "backend/infrastructure/persistence/__init__.py": '"""Persistence."""\n',
            "backend/infrastructure/persistence/stores/__init__.py": '"""Stores."""\n',
            "backend/infrastructure/persistence/stores/postgres_test_store.py": f"{rel_import}\n\nclass Store:\n    pass\n",
        }
        setup_tree(root, files)
        findings = check(root)
        assert any(f.rule == "INF002" for f in findings), (
            f"Expected INF002 for {rel_import}, got {findings}"
        )


# --- IH-006: Wildcard imports (INF003) ---
def test_wildcard_imports(tmp_path: Path) -> None:
    files = {
        "backend/infrastructure/__init__.py": '"""Root."""\n',
        "backend/infrastructure/persistence/__init__.py": '"""Persistence."""\n',
        "backend/infrastructure/persistence/stores/__init__.py": '"""Stores."""\n',
        "backend/infrastructure/persistence/stores/postgres_test_store.py": (
            "from backend.infrastructure.persistence.schemas.attachment_tables import *\n\n"
            "class Store:\n    pass\n"
        ),
    }
    setup_tree(tmp_path, files)
    findings = check(tmp_path)
    assert any(f.rule == "INF003" for f in findings)


# --- IH-007: Initializers and re-exports (INF004) ---
def test_initializers_and_reexport_only_modules(tmp_path: Path) -> None:
    # __init__.py with code should fail INF004
    files_bad_init = {
        "backend/infrastructure/__init__.py": "import os\n\nx = 1\n",
        "backend/infrastructure/persistence/__init__.py": '"""Persistence."""\n',
    }
    root1 = tmp_path / "bad_init"
    setup_tree(root1, files_bad_init)
    findings1 = check(root1)
    assert any(f.rule == "INF004" for f in findings1)

    # Re-export only module should fail INF004
    files_reexport = {
        "backend/infrastructure/__init__.py": '"""Root."""\n',
        "backend/infrastructure/persistence/__init__.py": '"""Persistence."""\n',
        "backend/infrastructure/persistence/stores/__init__.py": '"""Stores."""\n',
        "backend/infrastructure/persistence/stores/postgres_reexport_store.py": (
            '"""Re-export module."""\n'
            "from backend.infrastructure.persistence.stores.postgres_actual_store import ActualStore\n\n"
            "MyStore = ActualStore\n"
        ),
    }
    root2 = tmp_path / "reexport"
    setup_tree(root2, files_reexport)
    findings2 = check(root2)
    assert any(f.rule == "INF004" for f in findings2)


# --- IH-008: Onion and entrypoint edges (INF005) ---
def test_onion_and_entrypoint_edges(tmp_path: Path) -> None:
    # Outer layer depending directly on infrastructure
    files = {
        "backend/domain/model.py": "from backend.infrastructure.persistence.stores.postgres_auth_store import PostgresAuthentication\n",
        "backend/application/service.py": "from backend.infrastructure.persistence.stores.postgres_auth_store import PostgresAuthentication\n",
        "backend/infrastructure/__init__.py": '"""Root."""\n',
        "backend/infrastructure/persistence/__init__.py": '"""Persistence."""\n',
        "backend/infrastructure/persistence/stores/__init__.py": '"""Stores."""\n',
        "backend/infrastructure/persistence/stores/postgres_auth_store.py": (
            "from backend.presentation.routes import router\n\n"
            "class PostgresAuthentication:\n    pass\n"
        ),
    }
    setup_tree(tmp_path, files)
    findings = check(tmp_path)
    rules = [f.rule for f in findings]
    assert rules.count("INF005") >= 3


# --- IH-009: Adapter dependency directions (INF006) ---
def test_adapter_dependency_directions(tmp_path: Path) -> None:
    # llm -> intent (forbidden)
    files = {
        "backend/infrastructure/__init__.py": '"""Root."""\n',
        "backend/infrastructure/llm/__init__.py": '"""LLM."""\n',
        "backend/infrastructure/llm/gemini_provider.py": (
            "from backend.infrastructure.intent.jev_classifier import JevIntentClassifier\n\n"
            "class GeminiProvider:\n    pass\n"
        ),
    }
    setup_tree(tmp_path, files)
    findings = check(tmp_path)
    assert any(f.rule == "INF006" for f in findings)


# --- IH-010: Persistence and serialization roles (INF006) ---
def test_persistence_and_serialization_roles(tmp_path: Path) -> None:
    # schemas -> queries (forbidden)
    files = {
        "backend/infrastructure/__init__.py": '"""Root."""\n',
        "backend/infrastructure/persistence/__init__.py": '"""Persistence."""\n',
        "backend/infrastructure/persistence/schemas/__init__.py": '"""Schemas."""\n',
        "backend/infrastructure/persistence/schemas/metadata.py": (
            "from backend.infrastructure.persistence.queries.postgres_import_query_reader import PostgresImportQueries\n"
            "metadata = None\n"
        ),
    }
    setup_tree(tmp_path, files)
    findings = check(tmp_path)
    assert any(f.rule == "INF006" for f in findings)


# --- IH-011: Public modules, symbols, and consumers (INF007) ---
def test_public_modules_symbols_and_consumers(tmp_path: Path) -> None:
    # Importing a non-public symbol or from a forbidden consumer
    files = {
        "backend/infrastructure/__init__.py": '"""Root."""\n',
        "backend/infrastructure/persistence/__init__.py": '"""Persistence."""\n',
        "backend/infrastructure/persistence/queries/__init__.py": '"""Queries."""\n',
        "backend/infrastructure/persistence/queries/postgres_search_snapshot_provider.py": (
            "class PostgresRuntime:\n    pass\n\nclass _PrivateScope:\n    pass\n"
        ),
        # Forbidden consumer importing a restricted symbol
        "backend/infrastructure/llm/__init__.py": '"""LLM."""\n',
        "backend/infrastructure/llm/llm_provider_factory.py": (
            "from backend.infrastructure.persistence.queries.postgres_search_snapshot_provider import PostgresRuntime\n"
            "def create_llm_provider():\n    pass\n"
        ),
        # Allowed consumer importing an unexported private symbol
        "backend/infrastructure/composition/__init__.py": '"""Composition."""\n',
        "backend/infrastructure/composition/app_lifespan.py": (
            "from backend.infrastructure.persistence.queries.postgres_search_snapshot_provider import _PrivateScope\n"
            "def create_app_lifespan():\n    pass\n"
        ),
    }
    setup_tree(tmp_path, files)
    findings = check(tmp_path)
    rules = [f.rule for f in findings]
    assert "INF007" in rules


# --- IH-012: Import forms do not hide edges ---
def test_import_forms_do_not_hide_edges(tmp_path: Path) -> None:
    # Tests various import forms: as alias, module import, TYPE_CHECKING, inside function
    files = {
        "backend/infrastructure/__init__.py": '"""Root."""\n',
        "backend/infrastructure/persistence/__init__.py": '"""Persistence."""\n',
        "backend/infrastructure/persistence/stores/__init__.py": '"""Stores."""\n',
        "backend/infrastructure/persistence/stores/postgres_test_store.py": (
            "from typing import TYPE_CHECKING\n"
            "import backend.presentation.routes as pr\n\n"
            "if TYPE_CHECKING:\n"
            "    from backend.presentation.routes import SomeType\n\n"
            "def fn():\n"
            "    from backend.presentation.routes import local_route\n"
            "    return local_route\n"
        ),
    }
    setup_tree(tmp_path, files)
    findings = check(tmp_path)
    assert any(f.rule == "INF005" for f in findings)


# --- IH-013: Cycles and diamond graph (INF008) ---
def test_cycles_and_diamond_graph(tmp_path: Path) -> None:
    # Module A -> Module B -> Module A cycle
    files = {
        "backend/infrastructure/__init__.py": '"""Root."""\n',
        "backend/infrastructure/persistence/__init__.py": '"""Persistence."""\n',
        "backend/infrastructure/persistence/runtime/__init__.py": '"""Runtime."""\n',
        "backend/infrastructure/persistence/runtime/postgres_a.py": (
            "from backend.infrastructure.persistence.runtime.postgres_b import B\nclass A:\n    pass\n"
        ),
        "backend/infrastructure/persistence/runtime/postgres_b.py": (
            "from backend.infrastructure.persistence.runtime.postgres_a import A\nclass B:\n    pass\n"
        ),
    }
    setup_tree(tmp_path, files)
    findings = check(tmp_path)
    assert any(f.rule == "INF008" for f in findings)


# --- IH-014: Dynamic dependency bypasses (INF009) ---
def test_dynamic_dependency_bypasses(tmp_path: Path) -> None:
    files = {
        "backend/infrastructure/__init__.py": '"""Root."""\n',
        "backend/infrastructure/persistence/__init__.py": '"""Persistence."""\n',
        "backend/infrastructure/persistence/stores/__init__.py": '"""Stores."""\n',
        "backend/infrastructure/persistence/stores/postgres_bypass_store.py": (
            "import importlib\n"
            "mod = importlib.import_module('backend.presentation.routes')\n"
            "val = eval('1 + 1')\n"
            "exec('x = 2')\n"
        ),
    }
    setup_tree(tmp_path, files)
    findings = check(tmp_path)
    rules = [f.rule for f in findings]
    assert rules.count("INF009") >= 3


# --- IH-015: Repository role contract (INF010) ---
def test_repository_role_contract(tmp_path: Path) -> None:
    # Legitimate repository implementing domain repository protocol
    files_ok = {
        "backend/domain/order/repositories.py": "from typing import Protocol\nclass OrderRepository(Protocol):\n    def get(self): ...\n",
        "backend/infrastructure/__init__.py": '"""Root."""\n',
        "backend/infrastructure/persistence/__init__.py": '"""Persistence."""\n',
        "backend/infrastructure/persistence/repositories/__init__.py": '"""Repositories."""\n',
        "backend/infrastructure/persistence/repositories/postgres_order_repository.py": (
            "from backend.domain.order.repositories import OrderRepository as OrderPort\n\n"
            "class PostgresOrderRepository(OrderPort):\n    def get(self):\n        pass\n"
        ),
    }
    root1 = tmp_path / "repo_ok"
    setup_tree(root1, files_ok)
    findings1 = check(root1)
    assert not any(f.rule == "INF010" for f in findings1)

    # Pseudo-repository: named Repository but does not implement domain repository
    files_bad = {
        "backend/infrastructure/__init__.py": '"""Root."""\n',
        "backend/infrastructure/persistence/__init__.py": '"""Persistence."""\n',
        "backend/infrastructure/persistence/repositories/__init__.py": '"""Repositories."""\n',
        "backend/infrastructure/persistence/repositories/postgres_fake_repository.py": (
            "class PostgresFakeRepository:\n    def query(self):\n        pass\n"
        ),
    }
    root2 = tmp_path / "repo_bad"
    setup_tree(root2, files_bad)
    findings2 = check(root2)
    assert any(f.rule == "INF010" for f in findings2)


# --- IH-016: Models are ORM only (INF010) ---
def test_models_are_orm_only(tmp_path: Path) -> None:
    # Non-mapped plain dataclass placed in models/ should fail INF010
    files_bad = {
        "backend/infrastructure/__init__.py": '"""Root."""\n',
        "backend/infrastructure/persistence/__init__.py": '"""Persistence."""\n',
        "backend/infrastructure/persistence/models/__init__.py": '"""Models."""\n',
        "backend/infrastructure/persistence/models/order_model.py": (
            "from dataclasses import dataclass\n\n"
            "@dataclass\n"
            "class OrderModel:\n    id: str\n"
        ),
    }
    setup_tree(tmp_path, files_bad)
    findings = check(tmp_path)
    assert any(f.rule == "INF010" for f in findings)


# --- IH-017: Core tables and ORM are distinct (INF010) ---
def test_core_tables_and_orm_are_distinct(tmp_path: Path) -> None:
    # Defining sqlalchemy.Table in stores/ or queries/ should fail INF010
    files_bad = {
        "backend/infrastructure/__init__.py": '"""Root."""\n',
        "backend/infrastructure/persistence/__init__.py": '"""Persistence."""\n',
        "backend/infrastructure/persistence/stores/__init__.py": '"""Stores."""\n',
        "backend/infrastructure/persistence/stores/postgres_misplaced_table_store.py": (
            "from sqlalchemy import Table, Column, String, MetaData\n\n"
            "metadata = MetaData()\n"
            "my_table = Table('my_table', metadata, Column('id', String))\n"
        ),
    }
    setup_tree(tmp_path, files_bad)
    findings = check(tmp_path)
    assert any(f.rule == "INF010" for f in findings)


# --- IH-018: CLI contract and no source execution ---
def test_cli_contract_no_source_execution(tmp_path: Path) -> None:
    # Source with runtime side effects that must NOT be executed
    marker = tmp_path / "executed.marker"
    files = {
        "backend/infrastructure/__init__.py": f'"""Root."""\nimport os\nopen("{marker.as_posix()}", "w").close()\n',
    }
    config = setup_tree(tmp_path, files)
    code = main(["--root", str(tmp_path), "--config", str(config), "--json"])
    assert not marker.exists(), "Source was executed during AST checking!"
    assert code == 1


@pytest.mark.parametrize(
    "path,source,rule",
    [
        ("llm/banana.py", "value = 1", "INF001"),
        ("llm/openai_provider/deep/new_provider.py", "value = 1", "INF001"),
        ("cli/banana.py", "value = 1", "INF001"),
        (
            "llm/new_provider.py",
            "from backend import presentation\nvalue = 1",
            "INF005",
        ),
        (
            "llm/new_provider.py",
            "def run():\n    from backend import presentation\n    return presentation",
            "INF005",
        ),
        (
            "llm/new_provider.py",
            "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from backend import presentation\nvalue = 1",
            "INF005",
        ),
        (
            "llm/new_provider.py",
            "import backend.presentation.routes as routes\nvalue = routes.router",
            "INF005",
        ),
        (
            "composition/app_lifespan.py",
            "import backend.infrastructure.persistence.queries.postgres_search_snapshot_provider as p\nvalue = p._Scope",
            "INF007",
        ),
        (
            "llm/new_provider.py",
            "from importlib import import_module as load\nvalue = load('backend.main')",
            "INF009",
        ),
        (
            "persistence/registration/postgres_new_publisher.py",
            "from backend.infrastructure.persistence.queries.postgres_import_query_reader import PostgresImportQueries\nvalue = 1",
            "INF006",
        ),
        (
            "persistence/records/postgres_new_records.py",
            "from backend.application.attachment_import.queries.models import ImportDetail\nvalue = 1",
            "INF006",
        ),
        (
            "persistence/stores/postgres_new_store.py",
            "from sqlalchemy import Table as T\nvalue = T('bad', metadata)",
            "INF010",
        ),
        (
            "persistence/repositories/postgres_new_repository.py",
            "class LocalRepository: pass\nclass Fake(LocalRepository): pass",
            "INF010",
        ),
        (
            "persistence/models/new_model.py",
            "class NotOrmBase: pass\nclass Fake(NotOrmBase): pass",
            "INF010",
        ),
        (
            "persistence/schemas/new_tables.py",
            "from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column\nclass Base(DeclarativeBase): pass\nclass Row(Base):\n    __tablename__ = 'row'\n    id: Mapped[int] = mapped_column(primary_key=True)",
            "INF010",
        ),
        (
            "persistence/models/new_model.py",
            "from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column\nclass Base(DeclarativeBase): pass\nclass Row(Base):\n    __tablename__ = 'row'\n    id: Mapped[int] = mapped_column(primary_key=True)\nclass Plain: pass",
            "INF010",
        ),
    ],
)
def test_review_forbidden_forms(
    tmp_path: Path, path: str, source: str, rule: str
) -> None:
    """IH-002/010/012/014-017: each expression enforces its own rule."""
    setup_tree(tmp_path, {"backend/infrastructure/" + path: source + "\n"})
    assert any(f.rule == rule for f in check(tmp_path))


def test_package_import_cycle(tmp_path: Path) -> None:
    """IH-012/013: both from-package names are module edges."""
    setup_tree(
        tmp_path,
        {
            "backend/infrastructure/llm/a_provider.py": "from backend.infrastructure.llm import b_provider\nvalue = 1\n",
            "backend/infrastructure/llm/b_provider.py": "from backend.infrastructure.llm import a_provider\nvalue = 1\n",
        },
    )
    assert any(f.rule == "INF008" for f in check(tmp_path))


def test_new_adapter_subject_and_mapped_class(tmp_path: Path) -> None:
    """IH-001/016: role suffixes and actual registry mapping remain valid."""
    setup_tree(
        tmp_path,
        {
            "backend/infrastructure/llm/new_provider.py": "class NewProvider: pass\n",
            "backend/infrastructure/persistence/models/new_model.py": "from sqlalchemy.orm import registry, Mapped, mapped_column\nmapper_registry = registry()\n@mapper_registry.mapped\nclass Row:\n    __tablename__ = 'row'\n    id: Mapped[int] = mapped_column(primary_key=True)\n",
        },
    )
    assert check(tmp_path) == []


@pytest.mark.parametrize(
    "factory",
    [
        "from sqlalchemy.orm import declarative_base\nBase = declarative_base()",
        "from sqlalchemy.orm import declarative_base as create_base\nBase = create_base()",
        "import sqlalchemy.orm as orm\nBase = orm.declarative_base()",
    ],
)
def test_ih016_declarative_base_factory_is_orm(tmp_path: Path, factory: str) -> None:
    setup_tree(
        tmp_path,
        {
            "backend/infrastructure/persistence/models/order_model.py": factory
            + "\nfrom sqlalchemy import Column, Integer\nclass OrderModel(Base):\n    __tablename__ = 'orders'\n    id = Column(Integer, primary_key=True)\n",
        },
    )
    assert check(tmp_path) == []


@pytest.mark.parametrize(
    "definition",
    [
        "from sqlalchemy import MetaData\nmetadata = MetaData()",
        "from sqlalchemy import MetaData as M\nmetadata = M()",
        "import sqlalchemy as sa\nmetadata = sa.MetaData()",
    ],
)
def test_ih017_metadata_is_core_schema_only(tmp_path: Path, definition: str) -> None:
    setup_tree(
        tmp_path,
        {
            "backend/infrastructure/persistence/stores/postgres_order_store.py": definition
            + "\n",
        },
    )
    assert any(f.rule == "INF010" for f in check(tmp_path))
