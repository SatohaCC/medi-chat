"""医薬品の公開APIモデル。"""

from pydantic import BaseModel, ConfigDict, Field

MAX_PRODUCT_YJ_CODES = 50


class MedicineMatch(BaseModel):
    """照合・特定された医薬品情報モデル"""

    model_config = ConfigDict(from_attributes=True)

    generic_name: str
    brand_names: list[str]
    yj_codes: list[str]
    document_ids: list[str]
    matched_aliases: list[str] = Field(default_factory=list)
