"""医薬品カタログの公開Application入口。"""

from collections.abc import Sequence

from backend.application.medicine.interfaces.medicine_query_reader import (
    MedicineSnapshotProvider,
)
from backend.application.medicine.queries.policies.catalog_matching import (
    project_registered_product,
)
from backend.application.medicine.values import SearchGenerationId, parse_yj_codes


class MedicineQueries:
    def __init__(self, *, runtime: MedicineSnapshotProvider):
        self._runtime = runtime

    @staticmethod
    def validate_product_codes(values: Sequence[str]) -> None:
        """入力形式の検証を公開境界で行い、内部のPrimitiveは返さない。"""
        parse_yj_codes(values)

    async def read_autocomplete_catalog(
        self,
    ) -> tuple[SearchGenerationId, list[dict[str, str]]]:
        async with self._runtime.acquire() as snapshot:
            products = await snapshot.medicine_reader.read_medicines()
            items = [
                project_registered_product(product)
                for product in sorted(
                    products,
                    key=lambda product: (
                        product.yj_code.value if product.yj_code else ""
                    ),
                )
                if product.yj_code
            ]
            return snapshot.generation_id, items
