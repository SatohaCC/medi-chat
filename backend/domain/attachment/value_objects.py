"""添付文書ドメインの不変Value Object。

AttachmentRevision / Source / Product / Section は添付文書自体の構造を表す。
"""

from dataclasses import dataclass

from ..foundation.value_objects import ImmutableMapping
from ..json_types import JsonValue
from .primitives import (
    AttachmentBrandName,
    AttachmentEnglishName,
    AttachmentProductCode,
    AttachmentSectionTitle,
    AttachmentSha256,
    AttachmentUrl,
    NumberedSectionCode,
    RevisionSourceLabel,
    RevisionVersion,
    RevisionYearMonth,
)

# 添付文書自体: 改訂・原本の所在・掲載製品・項目階層


@dataclass(frozen=True, slots=True)
class AttachmentRevision:
    """添付文書の改訂情報。"""

    source_label: RevisionSourceLabel
    year_month: RevisionYearMonth
    version: RevisionVersion


@dataclass(frozen=True, slots=True)
class AttachmentSource:
    """原本ファイルとPMDA公開先を表す値。"""

    pmda_url: AttachmentUrl
    sha256: AttachmentSha256 | None = None


@dataclass(frozen=True, slots=True)
class AttachmentProduct:
    """添付文書に記載された製品の値。"""

    product_code: AttachmentProductCode
    brand_name: AttachmentBrandName
    english_name: AttachmentEnglishName | None = None


@dataclass(frozen=True, slots=True)
class AttachmentSection:
    """添付文書の項目番号と正式名称。"""

    code: NumberedSectionCode
    title: AttachmentSectionTitle

    @property
    def parent_code(self) -> NumberedSectionCode | None:
        """項目番号から導出した直接の親。"""
        return self.code.parent_code


@dataclass(frozen=True, slots=True, eq=False)
class AttachmentProductRevision(ImmutableMapping[JsonValue]):
    """医薬品情報の出典改訂。未知metadataを含む独立したスナップショット。"""


@dataclass(frozen=True, slots=True)
class AttachmentProductMatch:
    """照合・特定された医薬品情報。識別子を持つ製品Entityの投影値。"""

    generic_name: str
    brand_names: tuple[str, ...]
    yj_codes: tuple[str, ...]
    document_ids: tuple[str, ...]
    matched_aliases: tuple[str, ...] = ()
