"""医薬品の公開APIモデル。"""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

YJCode = Annotated[str, StringConstraints(pattern=r"^[0-9A-Z]{12}$")]


class MedicineMatch(BaseModel):
    """照合・特定された医薬品情報モデル"""

    model_config = ConfigDict(from_attributes=True)

    generic_name: str
    brand_names: list[str]
    yj_codes: list[str]
    document_ids: list[str]
    matched_aliases: list[str] = Field(default_factory=list)
