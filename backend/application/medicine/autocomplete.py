"""オートコンプリート用の医薬品カタログ投影ユースケース。"""

import unicodedata

from .product_contracts import MedicineSnapshotProvider
from .product_models import RegisteredMedicine, SearchGenerationId


def project_registered_product(product: RegisteredMedicine) -> dict[str, str]:
    """掲載製品だけのcompact投影。PMDAから不明な投与分類は既存の他。"""
    hiragana = unicodedata.normalize("NFKC", product.hiragana_name).lower()
    kana = "".join(
        chr(ord(char) + 0x60) if "ぁ" <= char <= "ゖ" else char for char in hiragana
    )
    return {
        "n": product.brand_name,
        "k": kana,
        "h": hiragana,
        "y": product.yj_code.value if product.yj_code else "",
        "g": product.generic_name,
        "c": "他",
    }


async def read_autocomplete_catalog(
    runtime: MedicineSnapshotProvider,
) -> tuple[SearchGenerationId, list[dict[str, str]]]:
    """現在の公開世代スナップショットからオートコンプリート候補一覧を取得する。"""
    async with runtime.acquire() as snapshot:
        products = await snapshot.medicine_reader.read_medicines()
        items = [
            project_registered_product(product)
            for product in sorted(
                products,
                key=lambda product: product.yj_code.value if product.yj_code else "",
            )
            if product.yj_code
        ]
        return snapshot.generation_id, items
