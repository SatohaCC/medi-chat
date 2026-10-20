"""添付文書索引の掲載製品を名称・製品コードで照合する処理。"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from backend.application.medicine.product_models import (
    RegisteredMedicine,
    ResolvedMedicine,
)
from backend.domain.medicine.primitives import BrandName, GenericName, ProductGroupId
from backend.domain.medicine.value_objects import MedicineMatch as DomainMedicineMatch

from ...domain.medicine.exceptions import MedicineDomainError
from ...domain.medicine.identifiers import YjCode


@dataclass(init=False)
class _ProductGroup:
    """照合中に製品と別名をまとめる、サービス内部の作業用状態。"""

    ingredient_id: ProductGroupId
    generic_name: str
    _medicines: list[RegisteredMedicine]

    def __init__(
        self,
        ingredient_id: ProductGroupId,
        generic_name: str,
        medicines: Sequence[RegisteredMedicine] | None = None,
    ) -> None:
        self.ingredient_id = ingredient_id
        self.generic_name = generic_name
        self._medicines = []
        for medicine in medicines or ():
            self.add_medicine(medicine)

    @property
    def medicines(self) -> list[RegisteredMedicine]:
        """集約内部を変更できないコピーとして製品Entityを返す。"""
        return list(self._medicines)

    def add_medicine(self, medicine: RegisteredMedicine) -> None:
        """同じ製品を重複させずに集約へ追加する。"""
        if medicine.ingredient_id != self.ingredient_id:
            raise MedicineDomainError("medicine must belong to the ingredient group")
        if all(
            (existing.document_id, existing.yj_code)
            != (medicine.document_id, medicine.yj_code)
            for existing in self._medicines
        ):
            self._medicines.append(medicine)

    @property
    def brand_names(self) -> list[str]:
        return list(
            dict.fromkeys(
                medicine.brand_name
                for medicine in self._medicines
                if medicine.brand_name
            )
        )

    @property
    def yj_codes(self) -> list[str]:
        return list(
            dict.fromkeys(
                medicine.yj_code.value
                for medicine in self._medicines
                if medicine.yj_code is not None and medicine.yj_code.value
            )
        )

    @property
    def document_ids(self) -> list[str]:
        return list(
            dict.fromkeys(medicine.document_id.value for medicine in self._medicines)
        )


class MedicineCatalog:
    """選択された製品コードを医薬品スナップショットへ照合するカタログ。"""

    def __init__(self, medicines: Sequence[RegisteredMedicine]) -> None:
        self._medicines = tuple(medicines)
        self._medicines_by_yj: dict[YjCode, tuple[RegisteredMedicine, ...]] = (
            self._index_medicines()
        )

    def _index_medicines(self) -> dict[YjCode, tuple[RegisteredMedicine, ...]]:
        indexed: dict[YjCode, list[RegisteredMedicine]] = {}
        for medicine in self._medicines:
            if medicine.yj_code is not None and medicine.yj_code.value:
                indexed.setdefault(medicine.yj_code, []).append(medicine)
        return {yj_code: tuple(medicines) for yj_code, medicines in indexed.items()}

    def _match_yj_groups(self, yj_codes: Sequence[YjCode]) -> list[_ProductGroup]:
        """指定されたYJコードに対応する医薬品グループを取得する。"""
        groups: dict[ProductGroupId, _ProductGroup] = {}
        for yj_code in dict.fromkeys(yj_codes):
            for medicine in self._medicines_by_yj.get(yj_code, ()):
                group = groups.setdefault(
                    medicine.ingredient_id,
                    _ProductGroup(
                        ingredient_id=medicine.ingredient_id,
                        generic_name=medicine.generic_name,
                    ),
                )
                group.add_medicine(medicine)
        return list(groups.values())

    @staticmethod
    def _match_result(group: _ProductGroup) -> ResolvedMedicine:
        return ResolvedMedicine(
            medicine=DomainMedicineMatch(
                generic_name=GenericName(group.generic_name)
                if group.generic_name
                else None,
                brand_names=tuple(BrandName(name) for name in group.brand_names),
                yj_codes=tuple(YjCode(code) for code in group.yj_codes),
            ),
            document_ids=tuple(group.document_ids),
        )

    def match_yj_codes(self, codes: Sequence[YjCode]) -> list[ResolvedMedicine]:
        """製品コードで照合し、不変の結果を返す。"""
        return [self._match_result(group) for group in self._match_yj_groups(codes)]

    def names_for_yj_codes(self, codes: Sequence[YjCode]) -> list[str]:
        """選択製品の登録名をキーワード抽出の除外語として返す。"""
        matched_medicines = [
            medicine
            for group in self._match_yj_groups(codes)
            for medicine in group.medicines
        ]
        raw_names: list[str] = []
        for med in matched_medicines:
            for name in (
                med.brand_name,
                med.generic_name,
                med.english_name,
                med.hiragana_name,
            ):
                if name:
                    raw_names.append(name)
                    # 括弧内の注記・屋号（例: 「SW」 -> SW）も除外語に含める
                    raw_names.extend(re.findall(r"[「\(（\[](.*?)[」\)）\]]", name))
        return list(dict.fromkeys(raw_names))
