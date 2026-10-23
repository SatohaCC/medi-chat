"""Browser oracle rejects DB source/structure/projection damage after migration."""

import copy
import json
import runpy

import pytest
from backend.infrastructure.persistence import postgres_schema as schema
from backend.tests.integration.test_postgres_registration import (
    pg_publisher as pg_publisher,
)
from backend.tests.integration.test_postgres_registration import publish
from backend.tests.support.paths import PROJECT_ROOT
from backend.tests.support.postgres_fixtures import pg_engines as pg_engines
from sqlalchemy import select, update

pytestmark = pytest.mark.source_data


@pytest.mark.parametrize("damage", [None, "source", "tree", "file", "index"])
def test_current_browser_oracle_detects_corruption(pg_engines, pg_publisher, damage):
    source = next(
        (PROJECT_ROOT / "data/pmda/originals").rglob("630004_3339003F5020_1_08.xml")
    )
    original = source.read_bytes()
    result = publish(pg_publisher, original)
    version_id = f"{result.document_id}:{result.source_sha256}"
    check = runpy.run_path(
        str(PROJECT_ROOT / "frontend/scripts/current-import-check.py")
    )["check"]
    assert check(source, pg_engines[1], version_id)["sections"] == 22
    if damage is None:
        return
    with pg_engines[0].begin() as connection:
        if damage == "source":
            connection.execute(
                update(schema.versions).values(source=b"x" * len(original))
            )
        elif damage == "tree":
            payload = copy.deepcopy(
                connection.execute(select(schema.versions.c.structure)).scalar_one()
            )
            payload["document"]["sections"][0]["code"] = "99"
            connection.execute(update(schema.versions).values(structure=payload))
        elif damage == "file":
            row = connection.execute(
                select(schema.units.c.unit_id, schema.units.c.payload_json).limit(1)
            ).one()
            value = json.loads(row.payload_json)
            value["text"] += "broken"
            connection.execute(
                update(schema.units)
                .where(schema.units.c.unit_id == row.unit_id)
                .values(payload_json=json.dumps(value))
            )
        else:
            connection.execute(update(schema.units).values(query_text="broken"))
    with pytest.raises(AssertionError):
        check(source, pg_engines[1], version_id)
