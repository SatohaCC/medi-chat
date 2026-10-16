"""オートコンプリート用の医薬品カタログ投影ユースケース。"""

import unicodedata

from backend.application.medicine.product_models import RegisteredMedicine
from backend.application.retrieval.snapshot_contracts import RetrievalSnapshotProvider

from ...domain.retrieval.identifiers import SearchGenerationId


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


def katakana_to_hiragana(text: str) -> str:
    """Convert Katakana characters to Hiragana."""
    return "".join(
        chr(ord(c) - 0x60) if 0x30A1 <= ord(c) <= 0x30F6 else c for c in text
    )


async def read_autocomplete_catalog(
    runtime: RetrievalSnapshotProvider,
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
