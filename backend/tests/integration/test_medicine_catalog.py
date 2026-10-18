"""文中の薬剤名とYJコードを解決する既存の優先順位を検証する。"""

from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path

import pytest
from backend.application.medicine.product_catalog import MedicineCatalog, _ProductGroup
from backend.application.medicine.product_models import RegisteredMedicine
from backend.domain.attachment.identifiers import DocumentId
from backend.domain.attachment.primitives import PmdaUrl
from backend.domain.attachment.value_objects import (
    AttachmentProductRevision,
    MedicineDocumentReference,
)
from backend.domain.medicine.entities import MedicineProduct
from backend.domain.medicine.exceptions import MedicineDomainError
from backend.domain.medicine.identifiers import YjCode
from backend.domain.medicine.services import collect_aliases, get_weighted_aliases
from backend.infrastructure.persistence import schema
from backend.infrastructure.persistence.medicine_reader import SqlAlchemyMedicineReader
from backend.infrastructure.persistence.sqlite_engine import create_sqlite_engine
from backend.tests.infrastructure.persistence.test_alembic_migrations import (
    _migrate_database,
)
from sqlalchemy import insert
from sqlalchemy.engine import URL


def _read_indexed_medicines(
    tmp_path: Path, expected: tuple[RegisteredMedicine, ...]
) -> tuple[RegisteredMedicine, ...]:
    source = tmp_path / "structured"
    source.mkdir()
    index_path = tmp_path / "medicines.sqlite3"
    _migrate_database(index_path, source)
    engine = create_sqlite_engine(
        URL.create("sqlite", database=index_path.as_posix()).render_as_string(
            hide_password=False
        )
    )
    try:
        # 既存fixtureのdoc0/doc1と全8項目を変更せず、そのまま実Core読取の入力にする。
        with engine.begin() as connection:
            for medicine in expected:
                values = {
                    "document_key": medicine.document_id.value,
                    "yj_code": medicine.yj_code.value
                    if medicine.yj_code is not None
                    else None,
                    "brand_name": medicine.brand_name,
                    "generic_name": medicine.generic_name,
                    "english_name": medicine.english_name,
                    "hiragana_name": medicine.hiragana_name,
                    "pmda_url": medicine.pmda_url.value,
                }
                values["revision"] = medicine.revision.to_dict()
                values["revision_json"] = json.dumps(
                    values.pop("revision"), ensure_ascii=False
                )
                connection.execute(insert(schema.medicines), values)
        actual = asyncio.run(SqlAlchemyMedicineReader(engine).read_medicines())
        assert actual == expected
        assert type(actual) is tuple
        assert all(type(medicine) is RegisteredMedicine for medicine in actual)
        return actual
    finally:
        engine.dispose()


@pytest.fixture
def indexed_medicines(tmp_path: Path) -> tuple[RegisteredMedicine, ...]:
    expected = tuple(
        RegisteredMedicine(
            medicine=MedicineProduct(
                yj_code=YjCode(f"1234567A000{index}"),
                brand_name=name,
                generic_name=name + "成分",
                english_name="",
                hiragana_name="",
            ),
            reference=MedicineDocumentReference(
                document_id=DocumentId(f"doc{index}"),
                pmda_url=PmdaUrl("https://example.test"),
                revision=AttachmentProductRevision({}),
            ),
        )
        for index, name in enumerate(["アルファ", "ベータ"])
    )
    return _read_indexed_medicines(tmp_path, expected)


def test_group_deduplicates_initial_and_added_products_and_aliases(indexed_medicines):
    medicine = indexed_medicines[0]
    products = [medicine, medicine]
    aliases = ["アルファ", "アルファ"]
    group = _ProductGroup(
        ingredient_id=medicine.ingredient_id,
        generic_name=medicine.generic_name,
        medicines=products,
        matched_aliases=aliases,
    )
    products.clear()
    aliases.clear()
    group.add_medicine(medicine)
    group.add_matched_alias("アルファ")
    assert group.medicines == [medicine]
    assert group.matched_aliases == ["アルファ"]


@pytest.mark.parametrize("form", ["錠", "カプセル", "テープ", "点眼液"])
def test_alias_service_preserves_names_and_priority_for_dosage_forms(
    indexed_medicines, form
):
    medicine = replace(
        indexed_medicines[0],
        medicine=replace(
            indexed_medicines[0].medicine, brand_name=f"アルファ{form}10mg"
        ),
    )
    aliases = dict(get_weighted_aliases(medicine.medicine))
    assert aliases["アルファ"] == 85
    assert aliases[f"アルファ{form}10mg"] == 90
    assert aliases["1234567a0000"] == 100
    assert collect_aliases([medicine.medicine, medicine.medicine]) == list(aliases)
    assert medicine.brand_name == f"アルファ{form}10mg"


@pytest.mark.parametrize("on_construction", [True, False])
def test_group_rejects_other_ingredient_without_changing_products(
    indexed_medicines, on_construction
):
    first, other = indexed_medicines
    if on_construction:
        with pytest.raises(MedicineDomainError, match="ingredient group"):
            _ProductGroup(
                ingredient_id=first.ingredient_id,
                generic_name=first.generic_name,
                medicines=[first, other],
            )
    else:
        group = _ProductGroup(
            ingredient_id=first.ingredient_id,
            generic_name=first.generic_name,
            medicines=[first],
        )
        with pytest.raises(MedicineDomainError, match="ingredient group"):
            group.add_medicine(other)
        assert group.medicines == [first]


@pytest.mark.parametrize(
    ("message", "codes", "expected_codes", "covered"),
    [
        ("アルファの副作用", ["1234567A0000"], ["1234567A0000"], True),
        ("ベータの副作用", ["1234567A0000"], ["1234567A0000"], True),
        ("副作用について", ["1234567A0000", "0000000A0000"], ["1234567A0000"], False),
        ("副作用について", ["0000000A0000"], [], False),
        (
            "副作用について",
            ["1234567A0000", "1234567A0001"],
            ["1234567A0000", "1234567A0001"],
            True,
        ),
        ("アルファの副作用", [], ["1234567A0000"], True),
        ("副作用について", [], [], True),
        ("副作用について", ["1234567A0000", "1234567A0000"], ["1234567A0000"], True),
    ],
)
def test_文中薬剤名と指定コードの優先順位を維持する(
    message: str,
    codes: list[str],
    expected_codes: list[str],
    covered: bool,
    indexed_medicines: tuple[RegisteredMedicine, ...],
) -> None:
    catalog = MedicineCatalog(indexed_medicines)
    groups = catalog.resolve_medicines(message, codes)
    assert [code for group in groups for code in group.yj_codes] == expected_codes
    assert catalog.covers_requested_products(groups, codes) is covered


def test_Core読取の一般名aliasと薬剤全情報を保持する(tmp_path: Path) -> None:
    expected = RegisteredMedicine(
        medicine=MedicineProduct(
            yj_code=YjCode("1234567A0002"),
            brand_name="商品ガンマ",
            generic_name="固有成分名",
            english_name="DistinctCompound",
            hiragana_name="しょうひんがんま",
        ),
        reference=MedicineDocumentReference(
            document_id=DocumentId("alias-doc"),
            pmda_url=PmdaUrl("https://example.test/original?key=1"),
            revision=AttachmentProductRevision(
                {
                    "date": "2026-09-30",
                    "source": {"label": "原文"},
                    "history": [1, None],
                }
            ),
        ),
    )
    medicines = _read_indexed_medicines(tmp_path, (expected,))
    catalog = MedicineCatalog(medicines)
    groups = catalog.resolve_medicines("固有成分名の副作用", [])
    assert len(groups) == 1
    assert groups[0].yj_codes == ("1234567A0002",)
    assert groups[0].matched_aliases == ("固有成分名",)
    assert "固有成分名" in catalog.aliases_for_yj_codes(groups[0].yj_codes)
    assert groups[0].brand_names == (expected.brand_name,)
    assert groups[0].generic_name == expected.generic_name
    assert groups[0].document_ids == (expected.document_id.value,)


def test_aliases_for_yj_codes_includes_raw_names_and_brackets(tmp_path: Path) -> None:
    expected = RegisteredMedicine(
        medicine=MedicineProduct(
            yj_code=YjCode("6179001F1025"),
            brand_name="イトラコナゾールカプセル50mg「SW」",
            generic_name="イトラコナゾールカプセル",
            english_name="",
            hiragana_name="",
        ),
        reference=MedicineDocumentReference(
            document_id=DocumentId("doc-sw"),
            pmda_url=PmdaUrl("https://example.test/sw"),
            revision=AttachmentProductRevision({}),
        ),
    )
    medicines = _read_indexed_medicines(tmp_path, (expected,))
    catalog = MedicineCatalog(medicines)
    aliases = catalog.aliases_for_yj_codes(["6179001F1025"])
    assert "イトラコナゾールカプセル50mg「SW」" in aliases
    assert "SW" in aliases
