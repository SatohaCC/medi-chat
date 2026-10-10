"""3つ以上のコンテキストから参照される、横断的なドメインプリミティブ。"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from unicodedata import normalize
from urllib.parse import urlparse

from backend.domain.foundation.exceptions import DomainValidationError
from backend.domain.foundation.primitives.base import DomainPrimitive


@dataclass(frozen=True, slots=True)
class BaseString(DomainPrimitive[str]):
    """NFKC正規化と前後の余白除去を行い、空文字を禁止する文字列基底。

    DDDの原則に則り、プリミティブ文字列はそもそも空文字を許容しない
    （不正な状態を持つインスタンスを生成させない）。
    値が存在しない可能性のある概念は、プリミティブ内部で空文字を持つのではなく
    型定義側で None（Optional）を使って表現する。
    """

    def _normalize(self, value: object) -> str:
        if not isinstance(value, str):
            raise DomainValidationError("値は文字列である必要があります。")
        return normalize("NFKC", value).strip()

    def validate(self) -> None:
        """派生型で固有の制約を追加する。"""
        if not self.value:
            raise DomainValidationError("値は空にできません。")


@dataclass(frozen=True, slots=True)
class BaseHttpUrl(BaseString):
    """参照先を保持し、ホストとポートを検証する空値禁止のHTTP(S) URL。"""

    def _normalize(self, value: object) -> str:
        """参照先を変えないよう、前後の余白だけを除去する。"""
        if not isinstance(value, str):
            raise DomainValidationError("値は文字列である必要があります。")
        return value.strip()

    def validate(self) -> None:
        super().validate()
        try:
            parsed = urlparse(self.value)
            hostname = parsed.hostname
            _ = parsed.port
        except (ValueError, AttributeError) as exc:
            raise DomainValidationError(
                f"{type(self).__name__} must be a valid URL"
            ) from exc
        if parsed.scheme not in {"http", "https"} or not hostname:
            raise DomainValidationError(f"{type(self).__name__} must be an HTTP(S) URL")


@dataclass(frozen=True, slots=True)
class BaseFiniteFloat(DomainPrimitive[float]):
    """boolを除く数値から有限なfloatを保持する基底。"""

    def _normalize(self, value: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise DomainValidationError("値は数値である必要があります。")
        numeric = float(value)
        if not isfinite(numeric):
            raise DomainValidationError("値は有限である必要があります。")
        return numeric

    def validate(self) -> None:
        """派生型で固有の範囲制約を追加する。"""
