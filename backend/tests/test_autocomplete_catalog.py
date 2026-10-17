"""医薬品候補は根拠Readerを要求せず、読取終了まで世代を所有する。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

import pytest
from backend.application.medicine.autocomplete import read_autocomplete_catalog
from backend.application.medicine.product_contracts import (
    MedicineSnapshot,
    RegisteredMedicineReader,
    SearchGenerationId,
)


@pytest.mark.asyncio
@pytest.mark.parametrize("fail_read", [False, True])
async def test_catalogue_keeps_and_releases_its_medicine_only_snapshot(fail_read):
    generation_id = SearchGenerationId("catalogue-generation")

    @dataclass(frozen=True)
    class Snapshot:
        generation_id: SearchGenerationId
        medicine_reader: RegisteredMedicineReader

    class Reader:
        async def read_medicines(self):
            assert provider.active
            if fail_read:
                raise RuntimeError("catalogue read failed")
            return ()

    class Provider:
        active = False
        released = False

        @asynccontextmanager
        async def acquire(self) -> AsyncIterator[MedicineSnapshot]:
            self.active = True
            try:
                yield Snapshot(generation_id=generation_id, medicine_reader=Reader())
            finally:
                self.active = False
                self.released = True

    provider = Provider()
    if fail_read:
        with pytest.raises(RuntimeError, match="catalogue read failed"):
            await read_autocomplete_catalog(provider)
    else:
        assert await read_autocomplete_catalog(provider) == (generation_id, [])
    assert provider.released
    assert not provider.active
