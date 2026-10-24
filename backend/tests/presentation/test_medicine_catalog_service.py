"""カタログ公開入口は内部ポートをAPIへ漏らさず、現在の世代を使う。"""

from unittest.mock import AsyncMock, Mock

from backend.presentation.medicine_routes import router
from backend.tests.support.retrieval_snapshot import FixedSnapshotProvider
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_autocomplete_facade_reads_and_releases_current_snapshot():
    reader = Mock()
    reader.read_medicines = AsyncMock(return_value=())
    provider = FixedSnapshotProvider(reader, Mock())
    app = FastAPI()
    app.include_router(router)
    app.state.generation_runtime = provider
    with TestClient(app) as client:
        response = client.get("/api/medicines/autocomplete")
    assert response.status_code == 200
    assert response.json() == {"generation_id": "test", "items": []}
    assert provider.entered == provider.exited == 1
    reader.read_medicines.assert_awaited_once()
