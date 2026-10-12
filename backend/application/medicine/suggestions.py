"""フォーム入力から医薬品候補を提示する。根拠検索とは独立して扱う。"""

from collections.abc import Iterable
from dataclasses import dataclass

from ...domain.attachment.identifiers import DocumentId
from ...domain.medicine.identifiers import YjCode
from ...domain.retrieval.identifiers import SearchGenerationId
from ...domain.shared.services import normalize_match_text


@dataclass(frozen=True, slots=True, kw_only=True)
class SuggestionProduct:
    """候補提示に必要な名称・公開ID・照合別名の入力スナップショット。"""

    group_name: str
    generic_name: str
    brand_name: str
    yj_code: YjCode | None
    document_id: DocumentId
    aliases: tuple[tuple[str, int], ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class MedicineSuggestion:
    """フォームへ提示する候補。文書IDは既存API用の参照情報。"""

    generic_name: str
    brand_names: tuple[str, ...]
    yj_codes: tuple[YjCode, ...]
    document_ids: tuple[DocumentId, ...]
    matched_aliases: tuple[str, ...] = ()


class MedicineSuggester:
    """読み取り専用の候補データから候補一覧・名称照合結果を返す。"""

    def __init__(
        self,
        products: tuple[SuggestionProduct, ...],
        *,
        generation_id: SearchGenerationId | None = None,
    ) -> None:
        self._products = products
        self.generation_id = generation_id

    def suggest(self, query: str | None = None) -> tuple[MedicineSuggestion, ...]:
        normalized = normalize_match_text(query or "")
        if not query or not query.strip():
            groups = self._group((product, "") for product in self._products)
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

        if not normalized:
            return ()

        matches: list[tuple[int, int, int, SuggestionProduct, str, int]] = []
        for index, product in enumerate(self._products):
            for alias_index, (alias, priority) in enumerate(product.aliases):
                start = normalized.find(alias)
                if start >= 0:
                    matches.append(
                        (start, index, alias_index, product, alias, priority)
                    )
        best: dict[str, int] = {}
        positions: dict[str, int] = {}
        for start, _, _, product, _, priority in matches:
            best[product.group_name] = max(
                best.get(product.group_name, priority), priority
            )
            positions[product.group_name] = min(
                positions.get(product.group_name, start), start
            )
        matches.sort(key=lambda match: (match[0] + len(match[4]), match[1], match[2]))
        groups = self._group(
            (product, alias)
            for _, _, _, product, alias, priority in matches
            if priority == best[product.group_name]
        )
        return tuple(groups[key] for key in sorted(groups, key=positions.__getitem__))

    @staticmethod
    def _group(
        matches: Iterable[tuple[SuggestionProduct, str]],
    ) -> dict[str, MedicineSuggestion]:
        grouped: dict[str, list[tuple[SuggestionProduct, str]]] = {}
        for product, alias in matches:
            grouped.setdefault(product.group_name, []).append((product, alias))
        results: dict[str, MedicineSuggestion] = {}
        for key, products in grouped.items():
            unique: dict[tuple[DocumentId, YjCode | None], SuggestionProduct] = {}
            for product, _ in products:
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
                matched_aliases=tuple(
                    dict.fromkeys(alias for _, alias in products if alias)
                ),
            )
        return results
