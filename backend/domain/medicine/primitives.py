"""医薬品名称の照合に使う単一値。"""

from dataclasses import dataclass

from ..foundation.primitives.primitives import BaseString


@dataclass(frozen=True, slots=True)
class ProductGroupId(BaseString):
    """名称照合で使う派生グループ識別値。成分同一性を保証しない。"""
