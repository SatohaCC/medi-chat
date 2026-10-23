"""The checker must reject synthetic forbidden edges, not just accept this checkout."""

from pathlib import Path

import pytest
from scripts.application_architecture import check, main

CONFIG = {
    "features": {
        "orders": {
            "depends_on": ["catalog"],
            "public_modules": ["commands.models", "queries.get_order"],
        },
        "catalog": {
            "depends_on": [],
            "public_modules": ["commands.models", "queries.get_product"],
        },
        "other": {"depends_on": [], "public_modules": ["commands.models"]},
    }
}


def write(root: Path, files: dict[str, str]) -> None:
    (root / "backend/application").mkdir(parents=True, exist_ok=True)
    for relative, source in files.items():
        path = root / "backend/application" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")


@pytest.mark.parametrize(
    "path,source,expected",
    [
        ("orders/create_order/handler.py", "", "APP001"),
        ("orders/commands/create_order.py", "from ..models import Order", "APP002"),
        (
            "orders/commands/create_order.py",
            "from backend.application.orders.commands.models import *",
            "APP003",
        ),
        (
            "orders/__init__.py",
            "from backend.application.orders.commands.models import Order",
            "APP004",
        ),
        (
            "orders/commands/models.py",
            "from backend.infrastructure.db import Session",
            "APP005",
        ),
        (
            "orders/commands/models.py",
            "from backend.config.settings import Settings",
            "APP005",
        ),
        ("orders/commands/models.py", "import pydantic", "APP005"),
        (
            "orders/commands/models.py",
            "from backend.application.orders.interfaces.reader import Reader",
            "APP006",
        ),
        (
            "orders/interfaces/reader.py",
            "from backend.application.orders.commands.services.orders_service import Service",
            "APP006",
        ),
        (
            "orders/commands/create_order.py",
            "from backend.application.orders.queries.get_order import get_order",
            "APP007",
        ),
        (
            "orders/queries/get_order.py",
            "from backend.application.orders.queries.list_orders import list_orders",
            "APP007",
        ),
        (
            "orders/commands/create_order.py",
            "from backend.application.other.commands.models import Item",
            "APP008",
        ),
        (
            "orders/commands/create_order.py",
            "from backend.application.catalog.interfaces.reader import Reader",
            "APP008",
        ),
        (
            "common/models.py",
            "from backend.application.orders.commands.models import Order",
            "APP009",
        ),
        (
            "orders/commands/create_order.py",
            "from concurrent.futures import ThreadPoolExecutor",
            "APP010",
        ),
        ("orders/commands/create_order.py", "import importlib as loader", "APP010"),
        (
            "orders/commands/create_order.py",
            "__import__('backend.infrastructure.db')",
            "APP011",
        ),
        ("orders/commands/create_order.py", "def broken(:", "APP000"),
    ],
)
def test_forbidden_examples_are_detected(tmp_path, path, source, expected):
    write(tmp_path, {path: source})
    assert expected in {finding.rule for finding in check(tmp_path, CONFIG)}


@pytest.mark.parametrize(
    "source",
    [
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import backend.infrastructure.db as db",
        "def execute():\n    from backend.infrastructure.db import Session",
    ],
)
def test_type_checking_and_local_imports_do_not_hide_edges(tmp_path, source):
    write(tmp_path, {"orders/commands/create_order.py": source})
    assert "APP005" in {f.rule for f in check(tmp_path, CONFIG)}


def test_package_form_resolves_the_actual_module(tmp_path):
    write(
        tmp_path,
        {
            "orders/commands/models.py": "from backend.application.orders.commands.services import orders_service as svc",
            "orders/commands/services/orders_service.py": "",
        },
    )
    assert "APP006" in {f.rule for f in check(tmp_path, CONFIG)}


def test_relative_import_is_also_checked_for_forbidden_target(tmp_path):
    write(
        tmp_path,
        {"orders/commands/models.py": "from ....infrastructure.db import Session"},
    )
    assert {"APP002", "APP005"} <= {f.rule for f in check(tmp_path, CONFIG)}


def test_valid_feature_slice_and_public_dependencies_are_allowed(tmp_path):
    write(
        tmp_path,
        {
            "orders/__init__.py": '"""Orders."""',
            "orders/commands/create_order.py": "from backend.application.orders.commands.models import Order\nfrom backend.application.orders.interfaces.writer import Writer\nfrom backend.application.catalog.commands.models import Product\nfrom backend.domain.orders.entities import OrderEntity",
            "orders/queries/get_order.py": "from backend.application.orders.queries.dtos.order_summary import Summary",
            "orders/interfaces/writer.py": "from backend.application.orders.commands.models import Order",
            "orders/policies.py": "from backend.application.orders.values import OrderId",
            "orders/commands/models.py": "from backend.application.orders.values import OrderId",
            "orders/values.py": "from backend.application.orders.errors import InvalidOrder",
            "orders/errors.py": "class InvalidOrder(Exception): pass",
            "orders/queries/dtos/order_summary.py": "from backend.application.orders.values import OrderId",
            "common/values.py": "from dataclasses import dataclass",
            "catalog/commands/models.py": "",
        },
    )
    assert not check(tmp_path, CONFIG)


def test_import_phase_does_not_claim_layout_is_migrated(tmp_path):
    write(
        tmp_path,
        {"orders/old_models.py": "from backend.domain.orders.entities import Order"},
    )
    assert not check(tmp_path, CONFIG, phase="imports")
    assert {f.rule for f in check(tmp_path, CONFIG)} == {"APP001"}


def test_cli_exit_codes_and_json(tmp_path, capsys):
    write(tmp_path, {"orders/commands/create_order.py": "import sqlalchemy"})
    config = tmp_path / "rules.toml"
    config.write_text(
        '[features.orders]\ndepends_on=[]\npublic_modules=["models"]\n',
        encoding="utf-8",
    )
    args = ["--root", str(tmp_path), "--config", str(config)]
    assert main(args + ["--json"]) == 1
    assert '"rule": "APP005"' in capsys.readouterr().out
    assert main(args + ["--feature", "missing"]) == 2
    assert "Unknown feature" in capsys.readouterr().err
    (tmp_path / "backend/application/orders/commands/create_order.py").write_text(
        "", encoding="utf-8"
    )
    assert main(args) == 0


def test_feature_filter_is_explicit_and_does_not_hide_other_findings(tmp_path):
    write(
        tmp_path,
        {
            "orders/commands/models.py": "",
            "catalog/commands/models.py": "import sqlalchemy",
        },
    )
    assert not check(tmp_path, CONFIG, feature="orders")
    assert any(f.rule == "APP005" for f in check(tmp_path, CONFIG))


@pytest.mark.parametrize(
    "files, rule",
    [
        ({"orders/commands/handler.py": ""}, "APP001"),
        ({"common/commands/create_order.py": ""}, "APP001"),
        (
            {"common/models.py": "from backend.domain.orders.entities import Order"},
            "APP009",
        ),
    ],
)
def test_generic_names_and_feature_knowledge_in_common_are_rejected(
    tmp_path, files, rule
):
    write(tmp_path, files)
    assert rule in {f.rule for f in check(tmp_path, CONFIG)}


def test_feature_dependency_cycles_are_configuration_errors(tmp_path):
    write(tmp_path, {})
    config = {
        "features": {
            "a": {"depends_on": ["b"]},
            "b": {"depends_on": ["a"]},
        }
    }
    with pytest.raises(ValueError, match="cycle"):
        check(tmp_path, config)


def test_unknown_dependency_is_a_configuration_error(tmp_path):
    write(tmp_path, {})
    with pytest.raises(ValueError, match="Unknown dependency"):
        check(tmp_path, {"features": {"a": {"depends_on": ["missing"]}}})


def test_repository_import_phase_is_enforced():
    import tomllib

    from backend.tests.support.paths import BACKEND_ROOT

    root = BACKEND_ROOT.parent
    with (BACKEND_ROOT / "application-architecture.toml").open("rb") as stream:
        config = tomllib.load(stream)
    findings = check(root, config, phase="imports")
    assert not findings, "\n".join(str(finding) for finding in findings)


@pytest.mark.parametrize(
    "source,rule",
    [
        (
            "from backend.application.orders.interfaces.writer import Writer",
            "APP008",
        ),
        ("from backend.application.orders.policies import policy", "APP013"),
    ],
)
def test_external_consumers_are_checked(tmp_path, source, rule):
    write(tmp_path, {"orders/interfaces/writer.py": "", "orders/policies.py": ""})
    path = tmp_path / "backend/presentation/routes.py"
    path.parent.mkdir(parents=True)
    path.write_text(source, encoding="utf-8")
    assert rule in {f.rule for f in check(tmp_path, CONFIG)}


def test_composition_can_import_declared_public_ports(tmp_path):
    write(tmp_path, {"orders/interfaces/writer.py": ""})
    path = tmp_path / "backend/infrastructure/composition.py"
    path.parent.mkdir(parents=True)
    path.write_text(
        "from backend.application.orders.interfaces.writer import Writer",
        encoding="utf-8",
    )
    config = {
        "features": {
            "orders": {
                "depends_on": [],
                "public_modules": ["interfaces.writer"],
            }
        }
    }
    assert not check(tmp_path, config)


@pytest.mark.parametrize(
    "source",
    [
        "from backend.application.catalog.commands import models as data",
        "import backend.application.catalog.commands.models as data",
        "from backend.application.catalog.commands.models import Product as Item",
    ],
)
def test_public_module_import_forms_are_equivalent(tmp_path, source):
    write(
        tmp_path,
        {"orders/commands/create_order.py": source, "catalog/commands/models.py": ""},
    )
    assert not check(tmp_path, CONFIG)


def test_cli_uses_script_root_when_called_from_another_directory(tmp_path, monkeypatch):
    import scripts.application_architecture as harness
    from backend.tests.support.paths import BACKEND_ROOT

    monkeypatch.chdir(tmp_path)
    assert harness.main(["--phase", "imports"]) == 0
    assert BACKEND_ROOT.is_dir()


def test_enforced_phase_checks_migrated_features_without_hiding_audit(tmp_path):
    write(tmp_path, {"orders/old_file.py": "", "catalog/old_file.py": ""})
    config = {**CONFIG, "enforced_features": ["orders"]}
    enforced = check(tmp_path, config, phase="enforced")
    assert len(enforced) == 1 and enforced[0].feature == "orders"
    assert len(check(tmp_path, config)) == 2


def test_enforced_phase_checks_external_consumers_of_migrated_feature(tmp_path):
    write(tmp_path, {"orders/interfaces/private.py": ""})
    path = tmp_path / "backend/presentation/routes.py"
    path.parent.mkdir(parents=True)
    path.write_text(
        "from backend.application.orders.interfaces.private import Writer",
        encoding="utf-8",
    )
    config = {**CONFIG, "enforced_features": ["orders"]}
    assert any(
        f.rule == "APP008" and f.feature == "orders"
        for f in check(tmp_path, config, phase="enforced")
    )


def test_repository_migrated_features_are_enforced():
    import tomllib

    from backend.tests.support.paths import BACKEND_ROOT

    with (BACKEND_ROOT / "application-architecture.toml").open("rb") as stream:
        config = tomllib.load(stream)
    assert not check(BACKEND_ROOT.parent, config, phase="enforced")


def test_reusable_services_and_policy_packages_are_allowed(tmp_path):
    write(
        tmp_path,
        {
            "orders/commands/create_order.py": "from backend.application.orders.commands.services.creation import create",
            "orders/commands/services/creation.py": "from backend.application.orders.policies.validation import validate\nfrom backend.application.orders.interfaces.writer import Writer",
            "orders/policies/validation.py": "from backend.application.orders.policies.limits import LIMIT",
            "orders/policies/limits.py": "LIMIT=1",
            "orders/interfaces/writer.py": "from backend.application.orders.interfaces.transaction import Transaction",
            "orders/interfaces/transaction.py": "",
        },
    )
    assert not check(tmp_path, CONFIG)


def test_port_composition_cycles_are_rejected(tmp_path):
    write(
        tmp_path,
        {
            "orders/interfaces/a.py": "from backend.application.orders.interfaces.b import B",
            "orders/interfaces/b.py": "from backend.application.orders.interfaces.a import A",
        },
    )
    assert any(f.rule == "APP012" for f in check(tmp_path, CONFIG))


def test_reusable_services_must_not_import_use_case_slices(tmp_path):
    write(
        tmp_path,
        {
            "orders/commands/services/creation.py": "from backend.application.orders.commands.create_order import execute"
        },
    )
    assert any(f.rule == "APP007" for f in check(tmp_path, CONFIG))


def test_public_cross_feature_use_cases_cannot_be_composed_inside_a_slice(tmp_path):
    write(
        tmp_path,
        {
            "orders/commands/create_order.py": "from backend.application.catalog.queries.get_product import execute"
        },
    )
    assert any(f.rule == "APP007" for f in check(tmp_path, CONFIG))


def test_repository_all_rules_and_declared_public_modules_exist():
    import tomllib

    from backend.tests.support.paths import BACKEND_ROOT

    with (BACKEND_ROOT / "application-architecture.toml").open("rb") as stream:
        config = tomllib.load(stream)
    assert not check(BACKEND_ROOT.parent, config)
    assert set(config["enforced_features"]) == set(config["features"])
    for feature, spec in config["features"].items():
        for public in spec["public_modules"]:
            path = BACKEND_ROOT / "application" / feature
            assert path.joinpath(*public.split(".")).with_suffix(".py").is_file(), (
                feature,
                public,
            )


@pytest.mark.parametrize("filename", ["service.py", "services.py"])
def test_root_services_are_rejected_even_when_single(tmp_path, filename):
    write(tmp_path, {f"orders/{filename}": ""})
    assert "APP001" in {f.rule for f in check(tmp_path, CONFIG)}


@pytest.mark.parametrize(
    "path,source,rule",
    [
        (
            "orders/commands/create_order.py",
            "from backend.application.orders.queries.dtos.order import Order",
            "APP014",
        ),
        (
            "orders/queries/get_order.py",
            "from backend.application.orders.commands.models import Order",
            "APP014",
        ),
        (
            "orders/commands/services/create.py",
            "from backend.application.catalog.queries.get_product import execute",
            "APP014",
        ),
        (
            "orders/interfaces/order_query_reader.py",
            "from backend.application.orders.commands.models import Order",
            "APP014",
        ),
        (
            "orders/queries/get_order.py",
            "from backend.domain.orders.repositories import OrderRepository",
            "APP015",
        ),
        (
            "orders/queries/services/read.py",
            "from backend.domain.orders import repositories as repo",
            "APP015",
        ),
        ("orders/services/shared.py", "", "APP001"),
        ("orders/models.py", "", "APP001"),
        ("orders/dtos/order.py", "", "APP001"),
        ("orders/ports/reader.py", "", "APP001"),
    ],
)
def test_cqrs_boundaries(tmp_path, path, source, rule):
    write(tmp_path, {path: source, "orders/queries/dtos/order.py": ""})
    if "import repositories" in source:
        domain = tmp_path / "backend/domain/orders"
        domain.mkdir(parents=True)
        (domain / "repositories.py").write_text("", encoding="utf-8")
    assert rule in {f.rule for f in check(tmp_path, CONFIG)}


def test_query_reader_and_dto_stay_on_read_side(tmp_path):
    write(
        tmp_path,
        {
            "orders/queries/get_order.py": "from backend.application.orders.interfaces.order_query_reader import OrderQueryReader",
            "orders/interfaces/order_query_reader.py": "from backend.application.orders.queries.dtos.order import Order",
            "orders/queries/dtos/order.py": "from dataclasses import dataclass",
        },
    )
    assert not check(tmp_path, CONFIG)


@pytest.mark.parametrize(
    "source",
    [
        "from backend.application.orders.queries import models as data",
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from backend.application.orders.queries.dtos.order import Order as Result",
        "def execute():\n    from backend.application.orders.queries.dtos.order import Order",
    ],
)
def test_cqrs_boundary_cannot_hide_in_package_or_local_import(tmp_path, source):
    write(
        tmp_path,
        {
            "orders/commands/create_order.py": source,
            "orders/queries/models.py": "",
            "orders/queries/dtos/order.py": "",
        },
    )
    assert "APP014" in {f.rule for f in check(tmp_path, CONFIG)}


def test_commands_cannot_share_common_read_dtos(tmp_path):
    write(
        tmp_path,
        {
            "orders/commands/create_order.py": "from backend.application.common.dtos.page import Page",
            "common/dtos/page.py": "",
        },
    )
    assert "APP014" in {f.rule for f in check(tmp_path, CONFIG)}


def test_shared_policy_cannot_hide_repository_dependency_from_queries(tmp_path):
    write(
        tmp_path,
        {
            "orders/policies/validation.py": "from backend.domain.orders.repositories import OrderRepository"
        },
    )
    assert "APP015" in {f.rule for f in check(tmp_path, CONFIG)}


def test_commands_can_read_domain_aggregates_for_update(tmp_path):
    write(
        tmp_path,
        {
            "orders/commands/create_order.py": "from backend.domain.orders.repositories import OrderRepository"
        },
    )
    assert not check(tmp_path, CONFIG)
