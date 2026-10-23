"""Exercise actual pytest collection without connecting to a database."""

from pathlib import Path

import pytest

pytest_plugins = ("pytester",)


@pytest.fixture
def selection_project(pytester):
    pytester.makeconftest(
        (Path(__file__).parents[2] / "conftest.py").read_text(encoding="utf-8")
    )
    pytester.makeini(
        "[pytest]\nmarkers =\n postgres: real database\n source_data: private originals\n"
    )
    return pytester


@pytest.mark.parametrize(
    ("arguments", "passed", "deselected"),
    [
        ([], 2, 3),
        (["-m", "not source_data"], 1, 4),
        (["--postgres", "-m", "postgres and not source_data"], 2, 3),
        (["--postgres"], 5, 0),
    ],
)
def test_test_groups_keep_local_and_ci_coverage_distinct(
    selection_project, arguments, passed, deselected
):
    pytester = selection_project
    pytester.makepyfile(
        """
import unittest
import pytest

@pytest.fixture
def pg_engines():
    return object()

@pytest.fixture
def application(pg_engines):
    return pg_engines

def test_pure_logic():
    pass

def test_transitive_database_dependency(application):
    assert application is not None

@pytest.mark.postgres
class TestDirectDatabase(unittest.TestCase):
    def test_direct_database_context(self):
        pass

@pytest.mark.source_data
def test_original_xml_without_database():
    pass

@pytest.mark.source_data
def test_original_xml_with_database(pg_engines):
    pass
"""
    )
    result = pytester.runpytest_subprocess(*arguments, "-q")
    result.assert_outcomes(passed=passed, deselected=deselected)


def test_local_run_hides_credentials_and_refuses_database_connections(
    selection_project, monkeypatch
):
    monkeypatch.setenv("TEST_DATABASE_URL", "do-not-use-owner-credentials")
    monkeypatch.setenv("TEST_RUNTIME_DATABASE_URL", "do-not-use-runtime-credentials")
    monkeypatch.setenv("OPENAI_API_KEY", "do-not-call-provider")
    selection_project.makepyfile(
        """
import os
import pytest
from sqlalchemy import create_engine

def test_isolated_environment():
    assert not os.environ.get('TEST_DATABASE_URL')
    assert not os.environ.get('TEST_RUNTIME_DATABASE_URL')
    assert not os.environ.get('OPENAI_API_KEY')
    assert os.environ['PYTHON_DOTENV_DISABLED'] == '1'
    engine = create_engine(os.environ['MEDI_CHAT_DATABASE_URL'])
    try:
        with pytest.raises(AssertionError, match='Local tests must not connect'):
            engine.connect()
    finally:
        engine.dispose()
"""
    )
    selection_project.runpytest_subprocess("-q").assert_outcomes(passed=1)


def test_explicit_postgres_run_without_credentials_fails_instead_of_skipping(
    selection_project, monkeypatch
):
    monkeypatch.setenv("PYTHONPATH", str(Path(__file__).parents[4]))
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    monkeypatch.delenv("TEST_RUNTIME_DATABASE_URL", raising=False)
    selection_project.makepyfile(
        """
from backend.tests.support.postgres_fixtures import pg_engines

def test_real_database(pg_engines):
    raise AssertionError('Must not run without credentials')
"""
    )
    result = selection_project.runpytest_subprocess("--postgres", "-q", "--tb=short")
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(
        ["*Explicit TEST_DATABASE_URL and TEST_RUNTIME_DATABASE_URL*"]
    )


def test_source_data_modules_can_be_collected_without_private_oracle_files(
    selection_project, monkeypatch
):
    monkeypatch.setenv("PYTHONPATH", str(Path(__file__).parents[4]))
    selection_project.makepyfile(
        """
import importlib
from pathlib import Path

def test_import_without_private_files(monkeypatch):
    original = Path.read_text
    def read_text(path, *args, **kwargs):
        if path.name in {
            'interaction_oracle_v6.json', 'postgres_public_catalogue_oracle.json'
        }:
            raise AssertionError('Private oracle must not be read during collection')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'read_text', read_text)
    for name in (
        'backend.tests.integration.test_interaction_xml_oracle',
        'backend.tests.integration.test_definition_public_oracle',
        'backend.tests.presentation.test_api_routes',
    ):
        importlib.import_module(name)
"""
    )
    selection_project.runpytest_subprocess("-q").assert_outcomes(passed=1)
