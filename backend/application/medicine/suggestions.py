"""登録済み医薬品の候補一覧を提示する。根拠検索とは独立して扱う。"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from ...domain.attachment.identifiers import DocumentId
from ...domain.medicine.identifiers import YjCode
from ...domain.shared.services import normalize_match_text
from .product_models import RegisteredMedicine, SearchGenerationId


@dataclass(frozen=True, slots=True, kw_only=True)
class SuggestionProduct:
    """候補提示に必要な名称・公開IDの入力スナップショット。"""

    group_name: str
    generic_name: str
    brand_name: str
    yj_code: YjCode | None
    document_id: DocumentId


@dataclass(frozen=True, slots=True, kw_only=True)
class MedicineSuggestion:
    """フォームへ提示する候補。文書IDは既存API用の参照情報。"""

    generic_name: str
    brand_names: tuple[str, ...]
    yj_codes: tuple[YjCode, ...]
    document_ids: tuple[DocumentId, ...]


class MedicineSuggester:
    """読み取り専用の候補データから全候補一覧を返す。"""

    def __init__(
        self,
        products: tuple[SuggestionProduct, ...],
        *,
        generation_id: SearchGenerationId | None = None,
    ) -> None:
        self._products = products
        self.generation_id = generation_id

    @classmethod
    def from_registered_medicines(
        cls,
        products: Iterable[RegisteredMedicine],
        *,
        generation_id: SearchGenerationId | None = None,
    ) -> MedicineSuggester:
        return cls(
            tuple(
                SuggestionProduct(
                    group_name=product.ingredient_id.value,
                    generic_name=product.generic_name,
                    brand_name=product.brand_name,
                    yj_code=product.yj_code,
                    document_id=product.document_id,
                )
                for product in products
            ),
            generation_id=generation_id,
        )

    def list_all(self) -> tuple[MedicineSuggestion, ...]:
        """全登録製品を一般名グループにまとめ、安定した順序で返す。"""
        groups = self._group(self._products)
        return tuple(
            sorted(
                groups.values(),
                key=lambda group: (
                    normalize_match_text(
                        group.brand_names[0]
                        if group.brand_names
                        else group.generic_name
                    ),
                    tuple(code.value for code in group.yj_codes),
                ),
            )
        )

    @staticmethod
    def _group(
        matches: Iterable[SuggestionProduct],
    ) -> dict[str, MedicineSuggestion]:
        grouped: dict[str, list[SuggestionProduct]] = {}
        for product in matches:
            grouped.setdefault(product.group_name, []).append(product)
        results: dict[str, MedicineSuggestion] = {}
        for key, products in grouped.items():
            unique: dict[tuple[DocumentId, YjCode | None], SuggestionProduct] = {}
            for product in products:
                unique.setdefault((product.document_id, product.yj_code), product)
            values = tuple(unique.values())
            results[key] = MedicineSuggestion(
                generic_name=values[0].generic_name,
                brand_names=tuple(
                    dict.fromkeys(
                        product.brand_name for product in values if product.brand_name
                    )
                ),
                yj_codes=tuple(
                    dict.fromkeys(
                        product.yj_code
                        for product in values
                        if product.yj_code is not None
                    )
                ),
                document_ids=tuple(
                    dict.fromkeys(product.document_id for product in values)
                ),
            )
        return results
