import unicodedata

from ...domain.attachment.entities import AttachmentProductRecord

# Map MHLW administration category code to human-readable label
CATEGORY_MAP: dict[str, str] = {
    "1": "内用",
    "2": "内用",
    "3": "歯科",
    "4": "注射",
    "6": "外用",
    "8": "他",
}


def project_registered_product(product: AttachmentProductRecord) -> dict[str, str]:
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


def project_yj_row(row: list[str]) -> dict[str, str] | None:
    if len(row) < 38:
        return None
    # Check validity: Col 30 is expiration date; 99999999 means active
    end_date = row[30].strip()
    if end_date != "99999999":
        return None

    name = row[4].strip()
    if not name:
        return None

    yj_code = row[31].strip()

    # Col 6 is half-width katakana reading
    raw_reading = unicodedata.normalize("NFKC", row[6].strip())
    hiragana_reading = katakana_to_hiragana(raw_reading).lower()

    generic_name = row[37].replace("【般】", "").strip()
    category_code = row[27].strip()
    category = CATEGORY_MAP.get(category_code, "他")

    return {
        "n": name,
        "k": raw_reading,
        "h": hiragana_reading,
        "y": yj_code,
        "g": generic_name,
        "c": category,
    }
