"""Entity・AggregateのID Primitiveに共通する基底。"""

import re
import uuid
from dataclasses import dataclass
from typing import ClassVar, Self

from ..exceptions import DomainValidationError
from .base import DomainPrimitive
from .primitives import BaseString


@dataclass(frozen=True, slots=True)
class EntityUUID(DomainPrimitive[uuid.UUID]):
    """エンティティの一意識別子（UUIDv7）を表す基底クラス。

    UUIDv7 を要求するのは、時刻順に並ぶIDにより「作成順」がIDだけで決まり、
    採番のために永続化層へ問い合わせずに済むため。採番は :meth:`generate`、
    文字列からの復元は :meth:`parse` を使い、``uuid.UUID`` を直に組み立てる
    箇所を1つに閉じ込める。
    """

    identifier_name: ClassVar[str] = "識別子"

    def validate(self) -> None:
        # 文字列などが渡されたときの AttributeError を防ぐ。
        if not isinstance(self.value, uuid.UUID):
            got = type(self.value).__name__
            raise DomainValidationError(
                f"{self.identifier_name}はUUIDインスタンスである必要があります。受け取った型: {got}。"
            )

        if self.value.version != 7:
            raise DomainValidationError(
                f"{self.identifier_name}はUUID v7である必要があります。"
            )

    @classmethod
    def generate(cls) -> Self:
        """Python標準ライブラリで新しいUUIDv7識別子を採番する。"""
        return cls(uuid.uuid7())  # type: ignore[attr-defined]

    @classmethod
    def parse(cls, raw: str | uuid.UUID) -> Self:
        """文字列表現（DBの列値・APIのパスパラメータ）から識別子を復元する。

        Raises:
            DomainValidationError: UUIDv7として解釈できない場合。呼び出し元が
                HTTPの4xxへ変換できるよう ``ValueError`` ではなくドメイン例外
                に統一している。
        """
        if isinstance(raw, uuid.UUID):
            return cls(raw)
        try:
            return cls(uuid.UUID(raw))
        except (ValueError, AttributeError, TypeError) as exc:
            raise DomainValidationError(
                f"{cls.identifier_name}はUUID形式の文字列である必要があります。受け取った値: {raw!r}。"
            ) from exc


@dataclass(frozen=True, slots=True)
class EntityStringId(BaseString):
    """NFKC正規化・前後の余白除去・空値拒否を行う文字列ID基底。"""

    value_pattern: ClassVar[str | None] = None

    def validate(self) -> None:
        super().validate()
        if (
            self.value_pattern is not None
            and re.fullmatch(self.value_pattern, self.value) is None
        ):
            raise DomainValidationError(f"{type(self).__name__} has an invalid format")

    @classmethod
    def parse(cls, raw: str) -> Self:
        """文字列から識別子を復元する。"""
        return cls(raw)
