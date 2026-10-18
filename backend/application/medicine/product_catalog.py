"""添付文書索引の掲載製品を名称・製品コードで照合する処理。"""

from __future__ import annotations

import re
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass, field

from backend.application.medicine.product_models import (
    RegisteredMedicine,
    ResolvedMedicine,
)
from backend.domain.medicine.primitives import ProductGroupId
from backend.domain.medicine.value_objects import MedicineMatch as DomainMedicineMatch

from ...domain.attachment.identifiers import DocumentId
from ...domain.medicine.exceptions import MedicineDomainError
from ...domain.medicine.identifiers import YjCode
from ...domain.medicine.services import (
    best_alias_priorities,
    collect_aliases,
    get_weighted_aliases,
)
from ...domain.shared.services import normalize_match_text


@dataclass(init=False)
class _ProductGroup:
    """照合中に製品と別名をまとめる、サービス内部の作業用状態。"""

    ingredient_id: ProductGroupId
    generic_name: str
    _medicines: list[RegisteredMedicine]
    _matched_aliases: list[str]

    def __init__(
        self,
        ingredient_id: ProductGroupId,
        generic_name: str,
        medicines: Sequence[RegisteredMedicine] | None = None,
        matched_aliases: Sequence[str] | None = None,
    ) -> None:
        self.ingredient_id = ingredient_id
        self.generic_name = generic_name
        self._medicines = []
        for medicine in medicines or ():
            self.add_medicine(medicine)
        self._matched_aliases = []
        for alias in matched_aliases or ():
            self.add_matched_alias(alias)

    @property
    def medicines(self) -> list[RegisteredMedicine]:
        """集約内部を変更できないコピーとして製品Entityを返す。"""
        return list(self._medicines)

    @property
    def matched_aliases(self) -> list[str]:
        """集約内部を変更できないコピーとして照合別名を返す。"""
        return list(self._matched_aliases)

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

    def add_matched_alias(self, alias: str) -> None:
        """照合に使われた別名を重複させずに記録する。"""
        if alias not in self._matched_aliases:
            self._matched_aliases.append(alias)

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


@dataclass(frozen=True)
class _MedicineAlias:
    medicine: RegisteredMedicine
    alias: str
    priority: int


@dataclass
class _AliasTrieNode:
    children: dict[str, int] = field(default_factory=dict)
    failure: int = 0
    outputs: list[_MedicineAlias] = field(default_factory=list)


class MedicineCatalog:
    """医薬品スナップショットを索引化し、名称・製品コードで照合するカタログ。"""

    def __init__(self, medicines: Sequence[RegisteredMedicine]) -> None:
        self._medicines = tuple(medicines)
        self._nodes = [_AliasTrieNode()]
        self._medicines_by_yj: dict[YjCode, tuple[RegisteredMedicine, ...]] = (
            self._index_medicines()
        )
        self._build_alias_index()

    def _index_medicines(self) -> dict[YjCode, tuple[RegisteredMedicine, ...]]:
        indexed: dict[YjCode, list[RegisteredMedicine]] = {}
        for medicine in self._medicines:
            if medicine.yj_code is not None and medicine.yj_code.value:
                indexed.setdefault(medicine.yj_code, []).append(medicine)
        return {yj_code: tuple(medicines) for yj_code, medicines in indexed.items()}

    def _build_alias_index(self) -> None:
        seen: set[tuple[str, DocumentId, YjCode | None]] = set()
        for medicine in self._medicines:
            for alias, priority in get_weighted_aliases(medicine.medicine):
                key = (alias, medicine.document_id, medicine.yj_code)
                if key in seen:
                    continue
                seen.add(key)
                self._insert_alias(alias, _MedicineAlias(medicine, alias, priority))
        self._build_failure_links()

    def _insert_alias(self, alias: str, target: _MedicineAlias) -> None:
        node_index = 0
        for char in alias:
            child_index = self._nodes[node_index].children.get(char)
            if child_index is None:
                child_index = len(self._nodes)
                self._nodes[node_index].children[char] = child_index
                self._nodes.append(_AliasTrieNode())
            node_index = child_index
        self._nodes[node_index].outputs.append(target)

    def _build_failure_links(self) -> None:
        queue: deque[int] = deque()
        for child_index in self._nodes[0].children.values():
            queue.append(child_index)
        while queue:
            node_index = queue.popleft()
            node = self._nodes[node_index]
            for char, child_index in node.children.items():
                queue.append(child_index)
                failure = node.failure
                while failure and char not in self._nodes[failure].children:
                    failure = self._nodes[failure].failure
                self._nodes[child_index].failure = self._nodes[failure].children.get(
                    char, 0
                )
                inherited = self._nodes[self._nodes[child_index].failure].outputs
                if inherited:
                    self._nodes[child_index].outputs.extend(inherited)

    def _match_aliases(
        self, message: str
    ) -> tuple[str, list[tuple[int, _MedicineAlias]]]:
        normalized = normalize_match_text(message)
        if not normalized:
            return normalized, []
        matches: list[tuple[int, _MedicineAlias]] = []
        node_index = 0
        for end_index, char in enumerate(normalized):
            while node_index and char not in self._nodes[node_index].children:
                node_index = self._nodes[node_index].failure
            node_index = self._nodes[node_index].children.get(char, 0)
            for target in self._nodes[node_index].outputs:
                matches.append((end_index - len(target.alias) + 1, target))
        return normalized, matches

    def _match_text_groups(self, message: str) -> list[_ProductGroup]:
        """入力テキストから言及された医薬品グループを解決する。"""
        normalized, matches = self._match_aliases(message)
        if not normalized:
            return []

        best_priority = best_alias_priorities(
            (target.medicine.ingredient_id, target.priority) for _, target in matches
        )

        grouped: dict[ProductGroupId, _ProductGroup] = {}
        for _, target in matches:
            medicine = target.medicine
            key = medicine.ingredient_id
            if target.priority != best_priority[key]:
                continue
            group = grouped.setdefault(
                key,
                _ProductGroup(ingredient_id=key, generic_name=medicine.generic_name),
            )
            group.add_medicine(medicine)
            group.add_matched_alias(target.alias)
        return sorted(
            grouped.values(),
            key=lambda group: min(
                (
                    start
                    for start, target in matches
                    if target.medicine.ingredient_id == group.ingredient_id
                ),
                default=len(normalized),
            ),
        )

    def _match_yj_groups(self, yj_codes: Sequence[str | YjCode]) -> list[_ProductGroup]:
        """指定されたYJコードに対応する医薬品グループを取得する。"""
        groups: dict[ProductGroupId, _ProductGroup] = {}
        for yj_code in dict.fromkeys(YjCode.from_value(value) for value in yj_codes):
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

    def _resolve_groups(
        self, message: str, product_yj_codes: Sequence[str]
    ) -> list[_ProductGroup]:
        """メッセージと指定製品コードから、検索対象の医薬品を解決する。"""
        requested_codes = tuple(YjCode.from_value(value) for value in product_yj_codes)
        message_groups = self._match_text_groups(message)
        if not requested_codes:
            return message_groups
        return self._match_yj_groups(requested_codes)

    @staticmethod
    def covers_requested_products(
        groups: Sequence[ResolvedMedicine], codes: Sequence[str]
    ) -> bool:
        """解決結果が指定された製品コードをすべて含むか判定する。"""
        resolved_codes = {code for group in groups for code in group.yj_codes}
        requested_codes = {YjCode.from_value(value).value for value in codes}
        return not requested_codes or requested_codes.issubset(resolved_codes)

    @staticmethod
    def _match_result(group: _ProductGroup) -> ResolvedMedicine:
        return ResolvedMedicine(
            medicine=DomainMedicineMatch(
                generic_name=group.generic_name,
                brand_names=tuple(group.brand_names),
                yj_codes=tuple(group.yj_codes),
                matched_aliases=tuple(group.matched_aliases),
            ),
            document_ids=tuple(group.document_ids),
        )

    def match_text(self, message: str) -> list[ResolvedMedicine]:
        """名称で照合し、内部状態から独立した不変の結果を返す。"""
        return [self._match_result(group) for group in self._match_text_groups(message)]

    def match_yj_codes(self, codes: Sequence[str | YjCode]) -> list[ResolvedMedicine]:
        """製品コードで照合し、不変の結果を返す。"""
        return [self._match_result(group) for group in self._match_yj_groups(codes)]

    def resolve_medicines(
        self, message: str, codes: Sequence[str]
    ) -> list[ResolvedMedicine]:
        """文中の名称と指定コードの優先順位で医薬品を解決する。"""
        return [
            self._match_result(group) for group in self._resolve_groups(message, codes)
        ]

    def aliases_for_yj_codes(self, codes: Sequence[str | YjCode]) -> list[str]:
        """指定製品の別名をキーワード抽出の除外語として返す。"""
        matched_medicines = [
            medicine.medicine
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
        return list(dict.fromkeys([*raw_names, *collect_aliases(matched_medicines)]))

    def question_name_candidates(self, name: str) -> frozenset[YjCode]:
        """スロット全体が既存別名に一致する製品だけを返す。"""
        normalized = normalize_match_text(name)
        return frozenset(
            medicine.yj_code
            for medicine in self._medicines
            if medicine.yj_code is not None
            and any(
                alias == normalized
                for alias, _ in get_weighted_aliases(medicine.medicine)
            )
        )

    def original_product_names(self) -> tuple[str, ...]:
        """販売名内の引用符を引用文と区別するための原名称。"""
        return tuple(
            dict.fromkeys(
                name
                for medicine in self._medicines
                for name in (
                    medicine.brand_name,
                    medicine.generic_name,
                    medicine.english_name,
                    medicine.hiragana_name,
                )
                if name
            )
        )
