"""添付文書の原本情報のPrimitive。"""

import re
from dataclasses import dataclass
from typing import Self

from ..foundation.exceptions import DomainValidationError
from ..foundation.primitives.base import DomainPrimitive
from ..foundation.primitives.primitives import (
    BaseHttpUrl,
    BaseString,
)


@dataclass(frozen=True, slots=True)
class RegistrationSequence(DomainPrimitive[int]):
    """原本版の初成功登録順。失敗や再送に割り当てない正整数。"""

    def validate(self) -> None:
        if type(self.value) is not int or self.value < 1:
            raise DomainValidationError(
                "registration sequence must be a positive integer"
            )


@dataclass(frozen=True, slots=True)
class RevisionSourceLabel(BaseString):
    """改訂情報の出典ラベル。"""


@dataclass(frozen=True, slots=True)
class RevisionYearMonth(BaseString):
    """YYYY-MM形式の改訂年月。"""

    def validate(self) -> None:
        super().validate()
        if re.fullmatch(r"\d{4}-(?:0[1-9]|1[0-2])", self.value) is None:
            raise DomainValidationError(
                f"RevisionYearMonth must be YYYY-MM: {self.value!r}"
            )


@dataclass(frozen=True, slots=True)
class RevisionVersion(BaseString):
    """添付文書の版表記。"""


@dataclass(frozen=True, slots=True)
class PmdaUrl(BaseString):
    """カタログ由来のPMDA参照文字列。HTTP形式の検証は既存契約に含まない。"""


@dataclass(frozen=True, slots=True)
class SectionCode(BaseString):
    """添付文書の項目コード。原本モデルでは番号形式も検証する。"""

    def require_numbered(self) -> Self:
        """番号付き項目を要求する原本・加工モデルの制約を適用する。"""
        if re.fullmatch(r"\d+(?:\.\d+)*", self.value) is None:
            raise DomainValidationError(
                f"{type(self).__name__} must be a dotted numeric code: {self!r}"
            )
        return self


@dataclass(frozen=True, slots=True)
class AttachmentSha256(BaseString):
    """原本ファイルのSHA-256ダイジェスト。"""

    def _normalize(self, value: object) -> str:
        return super()._normalize(value).lower()

    def validate(self) -> None:
        super().validate()
        if re.fullmatch(r"[0-9a-f]{64}", self.value) is None:
            raise DomainValidationError("sha256 must be a 64-character hex digest")


@dataclass(frozen=True, slots=True)
class AttachmentBrandName(BaseString):
    """添付文書に記載された販売名。"""


@dataclass(frozen=True, slots=True)
class AttachmentEnglishName(BaseString):
    """添付文書に記載された英語名。"""


@dataclass(frozen=True, slots=True)
class AttachmentSectionTitle(BaseString):
    """添付文書の正式な項目名。"""


@dataclass(frozen=True, slots=True)
class DefinitionTitle(DomainPrimitive[str]):
    """定義正本の名称。空白と全半角を含む原表記を保持する。"""

    def validate(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise DomainValidationError("definition title must be nonempty text")


@dataclass(frozen=True, slots=True)
class InteractionColumnId(DomainPrimitive[str]):
    """添付文書の構造化列識別子。既存識別値を保持する。"""

    def validate(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise DomainValidationError("interaction column ID must be nonempty text")


@dataclass(frozen=True, slots=True)
class NumberedSectionCode(SectionCode):
    """原本項目で使う番号形式の項目コード。"""

    def validate(self) -> None:
        super().validate()
        self.require_numbered()

    @property
    def parent_code(self) -> Self | None:
        """末尾の番号を除いた直接の親。最上位項目には親がない。"""
        parent, separator, _ = self.value.rpartition(".")
        return type(self)(parent) if separator else None


@dataclass(frozen=True, slots=True)
class AttachmentProductCode(BaseString):
    """添付文書に紐づく製品コード（通常はYJコード）。"""


@dataclass(frozen=True, slots=True)
class AttachmentUrl(BaseHttpUrl):
    """添付文書の外部参照URL。"""


@dataclass(frozen=True, slots=True)
class ProductGroupId(BaseString):
    """文書掲載製品を照合中にまとめるための派生識別値。"""


@dataclass(frozen=True, slots=True)
class AttachmentText(DomainPrimitive[str]):
    """空文字・空白・改行を含め原文を保持する。"""

    def validate(self) -> None:
        if not isinstance(self.value, str):
            raise DomainValidationError("original text must be created from str")


@dataclass(frozen=True, slots=True)
class AttachmentColumnIndex(DomainPrimitive[int]):
    """表内の0始まりの列位置。"""

    def validate(self) -> None:
        if type(self.value) is not int or self.value < 0:
            raise DomainValidationError("column index must be a nonnegative integer")


@dataclass(frozen=True, slots=True)
class AttachmentCellSpan(DomainPrimitive[int]):
    """セルが占める行数または列数。"""

    def validate(self) -> None:
        if type(self.value) is not int or self.value < 1:
            raise DomainValidationError("cell span must be a positive integer")
