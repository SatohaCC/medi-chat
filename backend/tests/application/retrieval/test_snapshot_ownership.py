import pytest
from backend.application.retrieval.search_keywords import search_evidence_by_keywords
from backend.tests.application.chat.test_answer_preparation import MedicineReader
from backend.tests.support.retrieval_snapshot import FixedSnapshotProvider


@pytest.mark.asyncio
@pytest.mark.parametrize("fails", [False, True])
async def test_keyword_search_acquires_and_releases_one_snapshot(fails):
    class Reader:
        async def search(self, criteria, medicines):
            if fails:
                raise RuntimeError("test read failure")
            return ()

    provider = FixedSnapshotProvider(MedicineReader(), Reader())
    if fails:
        with pytest.raises(RuntimeError, match="test read failure"):
            await search_evidence_by_keywords(
                "副作用", ["1234567A0000"], snapshot_provider=provider
            )
    else:
        assert (
            await search_evidence_by_keywords(
                "副作用", ["1234567A0000"], snapshot_provider=provider
            )
            == ()
        )
    assert provider.entered == provider.exited == 1
