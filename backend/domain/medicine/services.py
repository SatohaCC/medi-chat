"""医薬品名称の別名生成と照合候補の選択規則。"""

import re
import unicodedata
from collections.abc import Iterable, Sequence

from ..shared.services import normalize_match_text
from .entities import MedicineProduct
from .primitives import ProductGroupId

DOSAGE_FORM_SUFFIXES = (
    "ドライシロップ",
    "カプセル",
    "OD錠",
    "細粒",
    "顆粒",
    "シロップ",
    "坐剤",
    "貼付剤",
    "吸入剤",
    "錠",
    "散",
    "注",
)

# 抽出でのみ使う剤形を追加し、既存の対象と優先順を保持する。
DOSAGE_FORM_PATTERN = (
    "("
    + "|".join(
        re.escape(form)
        for form in (
            *DOSAGE_FORM_SUFFIXES,
            "テープ",
            "軟膏",
            "クリーム",
            "点眼液",
            "点鼻液",
            "ゼリー",
            "配合錠",
        )
    )
    + ")"
)
HIRAGANA_DOSAGE_FORM_PATTERN = r"(どらいしろっぷ|かぷせる|おーでぃーじょう|さいりゅう|かりゅう|しろっぷ|ざざい|じょう|さん|ちゅう|てーぷ|なんこう|くりーむ)$"
ENGLISH_DOSAGE_FORM_PATTERN = (
    r"\b(tablets?|capsules?|syrup|injections?|granules?|powder|drops?)\b"
)


def extract_base_brand_name(name: str) -> str:
    """括弧内の注記、剤形、規格を除去して基本販売名を抽出する。"""
    norm = unicodedata.normalize("NFKC", name)
    cleaned = re.sub(r"[「\(（\[].*?[」\)）\]]", "", norm)
    cleaned = re.sub(DOSAGE_FORM_PATTERN, "", cleaned)
    cleaned = re.sub(
        r"[\d\.]+\s*(mg|g|ml|μg|ug|%|万単位)?", "", cleaned, flags=re.IGNORECASE
    )
    return cleaned.strip()


def extract_base_hiragana_name(name: str) -> str:
    """末尾のひらがな剤形サフィックスや数値を除去する。"""
    norm = unicodedata.normalize("NFKC", name)
    cleaned = re.sub(HIRAGANA_DOSAGE_FORM_PATTERN, "", norm)
    cleaned = re.sub(r"[\d\.]+", "", cleaned)
    return cleaned.strip()


def extract_base_english_name(name: str) -> str:
    """英語表記の剤形や規格を除去する。"""
    cleaned = re.sub(ENGLISH_DOSAGE_FORM_PATTERN, "", name, flags=re.IGNORECASE)
    cleaned = re.sub(r"[\d\.]+\s*(mg|g|ml|ug)?", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def get_weighted_aliases(medicine: MedicineProduct) -> list[tuple[str, int]]:
    """薬品名、規格なし基本名、ひらがな、英語などの別名と優先度を返す。"""
    values: list[tuple[str, int]] = []
    if medicine.yj_code is not None and medicine.yj_code.value:
        values.append((medicine.yj_code.value, 100))
    if medicine.brand_name:
        values.append((medicine.brand_name, 90))
        base_brand = extract_base_brand_name(medicine.brand_name)
        if base_brand and base_brand != medicine.brand_name:
            values.append((base_brand, 85))
        for suffix in DOSAGE_FORM_SUFFIXES:
            position = medicine.brand_name.find(suffix)
            if position >= 3:
                values.append((medicine.brand_name[:position], 55))
                break
    if medicine.english_name:
        values.append((medicine.english_name, 80))
        base_en = extract_base_english_name(medicine.english_name)
        if base_en and base_en.lower() != medicine.english_name.lower():
            values.append((base_en, 75))
    if medicine.generic_name:
        values.append((medicine.generic_name, 60))
        base_gen = extract_base_brand_name(medicine.generic_name)
        if base_gen and base_gen != medicine.generic_name:
            values.append((base_gen, 58))
    if medicine.hiragana_name:
        values.append((medicine.hiragana_name, 50))
        base_hira = extract_base_hiragana_name(medicine.hiragana_name)
        if base_hira and base_hira != medicine.hiragana_name:
            values.append((base_hira, 48))
    deduplicated: dict[str, int] = {}
    for alias, priority in values:
        normalized = normalize_match_text(alias)
        if len(normalized) >= 3:
            deduplicated[normalized] = max(priority, deduplicated.get(normalized, 0))
    return list(deduplicated.items())


def collect_aliases(medicines: Sequence[MedicineProduct]) -> list[str]:
    """製品の照合別名を、最初に現れた順で重複なく返す。"""
    return list(
        dict.fromkeys(
            alias
            for medicine in medicines
            for alias, _ in get_weighted_aliases(medicine)
        )
    )


def best_alias_priorities(
    candidates: Iterable[tuple[ProductGroupId, int]],
) -> dict[ProductGroupId, int]:
    """同一照合グループの最優先値を返す。同点候補は排除しない。"""
    best: dict[ProductGroupId, int] = {}
    for group_id, priority in candidates:
        best[group_id] = max(best.get(group_id, priority), priority)
    return best
