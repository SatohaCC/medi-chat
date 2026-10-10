"""医薬品コード対応表のExcelを純粋な医薬品モデルへ変換する入力境界。"""

import asyncio
from datetime import date
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

from ...domain.foundation.exceptions import DomainValidationError
from ...domain.medicine.entities import Medicine
from ...domain.medicine.identifiers import YjCode
from ...domain.medicine.primitives import (
    GenericNameCode,
    GenericPrescriptionName,
    MedicineName,
    ReceiptCode,
)

_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_HEADERS = (
    "レセ電コード",
    "ＹＪコード",
    "一般名コード",
    "医薬品名称(レセ電コード)",
    "医薬品名称(ＹJコード)",
    "一般名処方の標準的記載",
    "適用開始年月日",
    "適用終了年月日",
    "廃止年月日(レセ電コード)",
    "廃止年月日(YJコード)",
)


def _date(value: str) -> date | None:
    if value in ("", "99999999"):
        return None
    if len(value) != 8 or not value.isascii() or not value.isdigit():
        raise ValueError(f"Invalid code table date: {value!r}")
    return date(int(value[:4]), int(value[4:6]), int(value[6:]))


class MedicineCodeTableReader:
    def __init__(self, path: Path) -> None:
        self._path = path

    async def read_medicines(self) -> tuple[Medicine, ...]:
        return await asyncio.to_thread(self._read_medicines)

    def _read_medicines(self) -> tuple[Medicine, ...]:
        with ZipFile(self._path) as archive:
            shared = []
            if "xl/sharedStrings.xml" in archive.namelist():
                root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
                shared = [
                    "".join(
                        node.text or ""
                        for node in (
                            *item.findall("m:t", _NS),
                            *item.findall("m:r/m:t", _NS),
                        )
                    )
                    for item in root.findall("m:si", _NS)
                ]
            root = ElementTree.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        found_header = False
        medicines = []
        codes: set[YjCode] = set()
        for row in root.findall("m:sheetData/m:row", _NS):
            cells: dict[str, str] = {}
            for cell in row.findall("m:c", _NS):
                raw = cell.findtext("m:v", default="", namespaces=_NS)
                if cell.get("t") == "s":
                    value = shared[int(raw)]
                elif cell.get("t") == "inlineStr":
                    value = "".join(
                        node.text or "" for node in cell.findall("m:is//m:t", _NS)
                    )
                else:
                    value = raw
                column = "".join(char for char in cell.attrib["r"] if char.isalpha())
                cells[column] = value
            values = tuple(cells.get(column, "") for column in "ABCDEFGHIJ")
            if not found_header:
                if tuple(value.strip() for value in values) == _HEADERS:
                    found_header = True
                continue
            if not any(values):
                continue
            try:
                start = _date(values[6])
                if start is None:
                    raise ValueError("effective_from is required")
                medicine = Medicine(
                    yj_code=YjCode(values[1]),
                    receipt_code=ReceiptCode(values[0]),
                    receipt_name=MedicineName(values[3]),
                    yj_name=MedicineName(values[4]),
                    generic_name_code=GenericNameCode(values[2]) if values[2] else None,
                    generic_prescription_name=GenericPrescriptionName(values[5])
                    if values[5]
                    else None,
                    effective_from=start,
                    effective_until=_date(values[7]),
                    receipt_discontinued_on=_date(values[8]),
                    yj_discontinued_on=_date(values[9]),
                )
                if medicine.yj_code in codes:
                    raise ValueError(f"Duplicate YJ code: {medicine.yj_code.value}")
                codes.add(medicine.yj_code)
                medicines.append(medicine)
            except (ValueError, TypeError, DomainValidationError) as exc:
                raise ValueError(
                    f"Invalid medicine code table row {row.get('r')}: {exc}"
                ) from exc
        if not found_header:
            raise ValueError("Medicine code table headers were not found")
        return tuple(medicines)
