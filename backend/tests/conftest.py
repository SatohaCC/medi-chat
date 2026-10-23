"""Keep ordinary test runs independent of PostgreSQL credentials."""

import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine

_LOCAL_ENVIRONMENT = pytest.StashKey[pytest.MonkeyPatch]()


def pytest_configure(config):
    if config.getoption("--postgres"):
        return
    # main.app is constructed at import time; construction needs a URL, not a DB.
    # Isolate local tests from developer credentials and external API keys.
    environment = pytest.MonkeyPatch()
    environment.setenv("PYTHON_DOTENV_DISABLED", "1")
    environment.setenv(
        "MEDI_CHAT_DATABASE_URL", "postgresql+psycopg://unused@127.0.0.1:1/unused"
    )
    for name in (
        "TEST_DATABASE_URL",
        "TEST_RUNTIME_DATABASE_URL",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "TYPESAFE_API_KEY",
        "JEV_API_KEY",
    ):
        environment.delenv(name, raising=False)
    config.stash[_LOCAL_ENVIRONMENT] = environment
    event.listen(Engine, "do_connect", _refuse_local_database_connection)


def _refuse_local_database_connection(*args, **kwargs):
    raise AssertionError(
        "Local tests must not connect to a database; mark real DB tests postgres "
        "and run them explicitly with --postgres."
    )


def pytest_unconfigure(config):
    if _LOCAL_ENVIRONMENT in config.stash:
        event.remove(Engine, "do_connect", _refuse_local_database_connection)
        config.stash[_LOCAL_ENVIRONMENT].undo()


def pytest_addoption(parser):
    parser.addoption(
        "--postgres",
        action="store_true",
        help="Include real PostgreSQL tests (requires explicit test database URLs).",
    )


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    for item in items:
        # fixturenames includes transitive dependencies, such as pg_api -> pg_engines.
        if "pg_engines" in item.fixturenames:
            item.add_marker(pytest.mark.postgres)

    if config.getoption("--postgres"):
        return

    selected, deselected = [], []
    for item in items:
        if item.get_closest_marker("postgres") is not None:
            deselected.append(item)
        else:
            selected.append(item)
    items[:] = selected
    config.hook.pytest_deselected(items=deselected)
