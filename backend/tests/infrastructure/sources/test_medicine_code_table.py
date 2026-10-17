"""医薬品コード対応表の全列・特殊日付・不正入力の境界を検証する。"""

import asyncio
from dataclasses import FrozenInstanceError
from datetime import date
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import pytest
from backend.domain.medicine.repositories import MedicineRepository
from backend.infrastructure.sources.medicine_code_table import MedicineCodeTableReader

HEADERS = [
    "レセ電コード",
    "ＹＪコード",
    "一般名コード",
    "医薬品名称(レセ電コード)\n",
    "医薬品名称(ＹJコード)\n",
    "一般名処方の標準的記載",
    "適用開始年月日",
    "適用終了年月日",
    "廃止年月日(レセ電コード)",
    "廃止年月日(YJコード)",
]
ROW = [
    "610406079",
    "2325003B2029",
    "2325003B2ZZZ",
    " ガスター散２％ ",
    "ガスター散２％",
    "【般】ファモチジン散２％",
    "20221031",
    "99999999",
    "99999999",
    "20260331",
]


def workbook(tmp_path, rows, headers=HEADERS):
    namespace = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    root = ET.Element(f"{{{namespace}}}worksheet")
    data = ET.SubElement(root, f"{{{namespace}}}sheetData")
    for index, values in enumerate([headers, *rows], 1):
        row = ET.SubElement(data, f"{{{namespace}}}row", r=str(index))
        for column, value in zip("ABCDEFGHIJ", values, strict=True):
            cell = ET.SubElement(
                row, f"{{{namespace}}}c", r=f"{column}{index}", t="inlineStr"
            )
            inline = ET.SubElement(cell, f"{{{namespace}}}is")
            ET.SubElement(inline, f"{{{namespace}}}t").text = value
    path = tmp_path / "code_table.xlsx"
    with ZipFile(path, "w") as archive:
        archive.writestr("xl/worksheets/sheet1.xml", ET.tostring(root))
    return path


def test_all_columns_are_preserved_without_document_information(tmp_path):
    reader: MedicineRepository = MedicineCodeTableReader(workbook(tmp_path, [ROW]))
    records = asyncio.run(reader.read_medicines())
    assert len(records) == 1
    medicine = records[0]
    assert medicine.yj_code.value == "2325003B2029"
    assert medicine.receipt_code.value == "610406079"
    assert medicine.generic_name_code is not None
    assert medicine.generic_name_code.value == "2325003B2ZZZ"
    assert medicine.receipt_name.value == " ガスター散２％ "
    assert medicine.yj_name.value == "ガスター散２％"
    assert medicine.generic_prescription_name is not None
    assert medicine.generic_prescription_name.value == "【般】ファモチジン散２％"
    assert medicine.effective_from == date(2022, 10, 31)
    assert medicine.effective_until is None
    assert medicine.receipt_discontinued_on is None
    assert medicine.yj_discontinued_on == date(2026, 3, 31)
    assert not hasattr(medicine, "document_id")
    field_name = "yj_name"
    with pytest.raises((FrozenInstanceError, AttributeError)):
        setattr(medicine, field_name, None)


def test_optional_codes_names_and_dates_remain_absent(tmp_path):
    row = ROW.copy()
    for index in (2, 5, 7, 8, 9):
        row[index] = ""
    medicine = asyncio.run(
        MedicineCodeTableReader(workbook(tmp_path, [row])).read_medicines()
    )[0]
    assert medicine.generic_name_code is None
    assert medicine.generic_prescription_name is None
    assert medicine.effective_until is None
    assert medicine.receipt_discontinued_on is None
    assert medicine.yj_discontinued_on is None


@pytest.mark.parametrize(
    "index,value",
    [(0, "123"), (1, ""), (6, "99999999"), (6, "20260230"), (7, "20261301")],
)
def test_invalid_rows_are_rejected_with_row_context(tmp_path, index, value):
    row = ROW.copy()
    row[index] = value
    with pytest.raises(ValueError, match="row 2"):
        asyncio.run(MedicineCodeTableReader(workbook(tmp_path, [row])).read_medicines())


def test_duplicate_yj_codes_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="Duplicate YJ code"):
        asyncio.run(
            MedicineCodeTableReader(workbook(tmp_path, [ROW, ROW])).read_medicines()
        )


def test_missing_headers_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="headers"):
        asyncio.run(
            MedicineCodeTableReader(
                workbook(tmp_path, [ROW], [""] * 10)
            ).read_medicines()
        )
