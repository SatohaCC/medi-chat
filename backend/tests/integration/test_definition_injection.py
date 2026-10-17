"""TC08/10/15/21: explicit purpose policies never return to the definition source."""

from dataclasses import replace
from types import MappingProxyType

import pytest
from backend.domain.medicine.value_objects import MedicineMatch as DomainMedicineMatch


def test_tc15_reader_and_mapping_use_injected_heading_policy(
    tmp_path, monkeypatch
) -> None:
    import asyncio
    import json

    from backend.application.medicine.product_models import ResolvedMedicine
    from backend.domain.retrieval.primitives import DetectionSource, SearchSectionCode
    from backend.domain.retrieval.value_objects import SearchCriteria
    from backend.infrastructure import evidence_mapping
    from backend.infrastructure.package_insert_definitions import loader
    from backend.infrastructure.persistence import evidence_reader
    from backend.infrastructure.persistence.sqlite_engine import create_sqlite_engine
    from backend.tests.support.storage_fixtures import (
        build_document_store,
        write_structured_document,
    )
    from sqlalchemy.engine import URL

    source = write_structured_document(tmp_path, unit_count=2)
    units_path = source / "test_001/search_units.jsonl"
    units = [
        json.loads(line) for line in units_path.read_text(encoding="utf-8").splitlines()
    ]
    units[0].update(kind="item", text="特別見出し")
    units[1].update(kind="item", text="保持する原文本文")
    units_path.write_text(
        "\n".join(json.dumps(unit, ensure_ascii=False) for unit in units),
        encoding="utf-8",
    )
    index = tmp_path / "headings.sqlite3"
    build_document_store(source, index)
    definitions = loader.get_package_insert_definitions()
    policy = replace(
        definitions.text_search_policy, scope_heading_texts=frozenset({"特別見出し"})
    )
    engine = create_sqlite_engine(
        URL.create("sqlite", database=index.as_posix()).render_as_string(
            hide_password=False
        )
    )
    reader = evidence_reader.SqlAlchemyEvidenceReader(engine, text_search_policy=policy)

    def forbid(*args, **kwargs):
        pytest.fail("explicit reader policy reloaded definition source")

    monkeypatch.setattr(loader, "get_package_insert_definitions", forbid)
    monkeypatch.setattr(loader, "load_package_insert_definitions", forbid)
    monkeypatch.setattr(evidence_reader, "get_package_insert_definitions", forbid)
    assert evidence_mapping.is_scope_heading_only(units[0], text_search_policy=policy)
    assert not evidence_mapping.is_scope_heading_only(
        units[0], text_search_policy=definitions.text_search_policy
    )
    try:
        rows = asyncio.run(
            reader.search(
                SearchCriteria(
                    source=DetectionSource.LOGIC,
                    section_codes=(SearchSectionCode("11.1"),),
                ),
                (
                    ResolvedMedicine(
                        medicine=DomainMedicineMatch("", (), ("1234567A0000",), ()),
                        document_ids=("test_001",),
                    ),
                ),
            )
        )
        assert [row.unit_id.value for row in rows] == ["test_001:001"]
        assert [row.excerpt for row in rows] == ["保持する原文本文"]
    finally:
        engine.dispose()


def test_janome_business_and_morphology_settings_are_independent(monkeypatch) -> None:
    from backend.infrastructure.morphology.definition_settings import (
        JanomeMorphologySettings,
    )
    from backend.infrastructure.morphology.janome_keyword_extractor import (
        JanomeKeywordExtractor,
    )
    from backend.infrastructure.package_insert_definitions import loader

    definitions = loader.get_package_insert_definitions()
    default = JanomeKeywordExtractor(
        search_policy=definitions.text_search_policy,
        morphology_settings=definitions.morphology_settings,
    )
    business = JanomeKeywordExtractor(
        search_policy=replace(
            definitions.text_search_policy,
            stop_words=definitions.text_search_policy.stop_words | {"改善"},
            symptom_keywords_by_adjective=MappingProxyType({"眠い": ("眠気変更",)}),
        ),
        morphology_settings=definitions.morphology_settings,
    )
    morphology = JanomeKeywordExtractor(
        search_policy=definitions.text_search_policy,
        morphology_settings=JanomeMorphologySettings(ignored_noun_suffixes=frozenset()),
    )

    def forbid(*args, **kwargs):
        pytest.fail("explicit Janome settings reloaded definition source")

    monkeypatch.setattr(loader, "get_package_insert_definitions", forbid)
    monkeypatch.setattr(loader, "load_package_insert_definitions", forbid)
    assert default.extract_keywords("改善点") == ("改善",)
    assert morphology.extract_keywords("改善点") == ("改善点", "改善")
    assert business.extract_keywords("改善点") == ()
    assert business.extract_keywords("眠い") == ("眠気変更",)
    assert default.extract_keywords("眠い") == ("眠気", "傾眠")
