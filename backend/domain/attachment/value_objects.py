"""添付文書ドメインの不変Value Object。

AttachmentRevision / Source / Product / Section は添付文書自体の構造を表す。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..foundation.json_types import JsonValue
from ..foundation.value_objects import ImmutableMapping
from ..medicine.identifiers import YjCode
from .exceptions import (
    AttachmentDomainError,
    MissingOrInvalidYjError,
)
from .identifiers import DocumentId
from .primitives import (
    AttachmentBrandName,
    AttachmentCellSpan,
    AttachmentColumnIndex,
    AttachmentEnglishName,
    AttachmentProductCode,
    AttachmentSectionTitle,
    AttachmentSha256,
    AttachmentSourceOrder,
    AttachmentText,
    AttachmentUrl,
    DefinitionTitle,
    DocumentVersionId,
    InteractionColumnId,
    NumberedSectionCode,
    PmdaUrl,
    RevisionSourceLabel,
    RevisionVersion,
    RevisionYearMonth,
    SectionScope,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class SectionDefinition:
    code: NumberedSectionCode
    title: DefinitionTitle
    scope: SectionScope


@dataclass(frozen=True, slots=True, kw_only=True)
class SectionTaxonomy:
    sections: tuple[SectionDefinition, ...]

    def __post_init__(self) -> None:
        codes = tuple(section.code for section in self.sections)
        if len(codes) != len(set(codes)):
            raise AttachmentDomainError("duplicate section definition")
        for code in codes:
            if code.parent_code is not None and code.parent_code not in codes:
                raise AttachmentDomainError("unknown parent section definition")


@dataclass(frozen=True, slots=True, kw_only=True)
class InteractionColumnDefinition:
    id: InteractionColumnId
    title: DefinitionTitle


@dataclass(frozen=True, slots=True, kw_only=True)
class RegistrationVersion:
    document_id: DocumentId
    source_sha256: AttachmentSha256
    yj_codes: frozenset[YjCode]
    revised_at: RevisionYearMonth

    def __post_init__(self) -> None:
        if not self.yj_codes:
            raise MissingOrInvalidYjError("registration requires at least one YJ code")

    @property
    def version_id(self) -> DocumentVersionId:
        return DocumentVersionId(f"{self.document_id}:{self.source_sha256}")


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentReferenceTarget:
    """原文内で参照可能な要素。タグや保存形式には依存しない。"""

    reference_id: AttachmentText
    text: AttachmentText
    context: AttachmentContext = field(default_factory=lambda: AttachmentContext())


@dataclass(frozen=True, slots=True, eq=False)
class AttachmentMetadata(ImmutableMapping[JsonValue]):
    """原本の未知metadataも失わない独立した値。"""


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentContext:
    """原文の適用対象と文脈の順序。"""

    product_codes: tuple[AttachmentProductCode, ...] = ()
    labels: tuple[AttachmentText, ...] = ()
    # 文書全体での出現順。同じ文脈の隣接表行の結合判定には含めない。
    source_order: AttachmentSourceOrder | None = field(default=None, compare=False)


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentReference:
    """本文中の参照表示と原文内の参照先。"""

    label: AttachmentText
    target_id: AttachmentText | None = None
    metadata: AttachmentMetadata = field(default_factory=AttachmentMetadata)


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentTableCell:
    """原文セルと結合情報。列番号は0から始める。"""

    text: AttachmentText
    column: AttachmentColumnIndex
    rowspan: AttachmentCellSpan = field(default_factory=lambda: AttachmentCellSpan(1))
    colspan: AttachmentCellSpan = field(default_factory=lambda: AttachmentCellSpan(1))
    references: tuple[AttachmentReference, ...] = ()
    context: AttachmentContext = field(default_factory=AttachmentContext)


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentTable:
    """列と行の対応を保つ原文表。"""

    columns: tuple[AttachmentText, ...]
    rows: tuple[tuple[AttachmentTableCell, ...], ...]
    column_contexts: tuple[AttachmentContext, ...] = ()

    def __post_init__(self) -> None:
        if self.column_contexts and len(self.column_contexts) != len(self.columns):
            raise AttachmentDomainError("table column contexts must match headings")


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentParagraph:
    text: AttachmentText
    is_heading: bool = False
    context: AttachmentContext = field(default_factory=AttachmentContext)
    references: tuple[AttachmentReference, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentTableBlock:
    table: AttachmentTable
    context: AttachmentContext = field(default_factory=AttachmentContext)
    references: tuple[AttachmentReference, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentFigure:
    reference: AttachmentText
    description: AttachmentText
    context: AttachmentContext = field(default_factory=AttachmentContext)
    references: tuple[AttachmentReference, ...] = ()


type AttachmentBlock = AttachmentParagraph | AttachmentTableBlock | AttachmentFigure


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentBody:
    """子項目の本文を含まない、項目自身の順序付き原文本文。"""

    blocks: tuple[AttachmentBlock, ...] = ()
    text: AttachmentText | None = None


# 添付文書自体: 改訂・原本の所在・掲載製品・項目階層


@dataclass(frozen=True, slots=True)
class AttachmentRevision:
    """添付文書の改訂情報。"""

    source_label: RevisionSourceLabel
    year_month: RevisionYearMonth
    version: RevisionVersion
    metadata: AttachmentMetadata = field(default_factory=AttachmentMetadata)


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
    """標準項目名と原文見出しを区別し、配下の項目を所有する。"""

    code: NumberedSectionCode
    title: AttachmentSectionTitle
    body: AttachmentBody | None = None
    header: AttachmentText | None = None
    children: tuple[AttachmentSection, ...] = ()

    def __post_init__(self) -> None:
        if any(child.parent_code != self.code for child in self.children):
            raise AttachmentDomainError(
                "section children must have the owning parent code"
            )

    def walk(self) -> tuple[AttachmentSection, ...]:
        """自身と配下を保存順に返す。"""
        return (self, *(section for child in self.children for section in child.walk()))

    @property
    def parent_code(self) -> NumberedSectionCode | None:
        """項目番号から導出した直接の親。"""
        return self.code.parent_code


@dataclass(frozen=True, slots=True, eq=False)
class AttachmentProductRevision(ImmutableMapping[JsonValue]):
    """医薬品情報の出典改訂。未知metadataを含む独立したスナップショット。"""


@dataclass(frozen=True, slots=True)
class MedicineDocumentReference:
    """医薬品情報の出典となる添付文書参照。"""

    document_id: DocumentId
    pmda_url: PmdaUrl
    revision: AttachmentProductRevision


STANDARD_SECTION_TAXONOMY = SectionTaxonomy(
    sections=(
        SectionDefinition(
            code=NumberedSectionCode("1"),
            title=DefinitionTitle("警告"),
            scope=SectionScope(
                "使用に際して特に警告される重大な危険性と、その危険を避けるための投与条件・注意事項"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("2"),
            title=DefinitionTitle("禁忌"),
            scope=SectionScope(
                "投与してはいけない患者・状態。患者の疾患、既往歴等に基づく投与禁止事項"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("3"),
            title=DefinitionTitle("組成・性状"),
            scope=SectionScope(
                "製剤の組成と性状、製法の概要。有効成分・添加剤と、剤形・外観・識別に関する情報"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("3.1"),
            title=DefinitionTitle("組成"),
            scope=SectionScope(
                "製品・構成単位ごとの有効成分名と含有量、添加剤名と含有量、組成の概要・注釈"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("3.2"),
            title=DefinitionTitle("製剤の性状"),
            scope=SectionScope(
                "製品・構成単位ごとの剤形、色調、外形、大きさ、重量、識別コードなどの製剤の物理的性状"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("4"),
            title=DefinitionTitle("効能又は効果"),
            scope=SectionScope(
                "承認された効能又は効果。治療・予防・診断等の対象となる疾患や状態"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("5"),
            title=DefinitionTitle("効能又は効果に関連する注意"),
            scope=SectionScope(
                "効能又は効果に関連する使用対象の選択・適用条件・制限などの注意事項"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("6"),
            title=DefinitionTitle("用法及び用量"),
            scope=SectionScope(
                "投与量、投与回数・間隔、投与経路・方法などの定められた用法及び用量"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("7"),
            title=DefinitionTitle("用法及び用量に関連する注意"),
            scope=SectionScope(
                "用法及び用量に関連する投与量の調節、投与期間、休薬・再開、投与方法等の注意事項"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("8"),
            title=DefinitionTitle("重要な基本的注意"),
            scope=SectionScope(
                "使用全般における重要な基本的注意。投与前・投与中の確認、観察・検査や患者への説明等"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("9"),
            title=DefinitionTitle("特定の背景を有する患者に関する注意"),
            scope=SectionScope(
                "合併症・既往歴、腎・肝機能、生殖能、妊娠・授乳、年齢など特定の患者背景に応じた投与上の注意"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("9.1"),
            title=DefinitionTitle("合併症・既往歴等のある患者"),
            scope=SectionScope(
                "合併症・既往歴等のある患者に対する投与上の注意と、その患者背景に伴う危険性"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("9.2"),
            title=DefinitionTitle("腎機能障害患者"),
            scope=SectionScope(
                "腎機能障害のある患者に対する投与上の注意。腎機能の程度や透析等の背景に応じた留意事項"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("9.3"),
            title=DefinitionTitle("肝機能障害患者"),
            scope=SectionScope(
                "肝機能障害のある患者に対する投与上の注意。肝機能の程度等の背景に応じた留意事項"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("9.4"),
            title=DefinitionTitle("生殖能を有する者"),
            scope=SectionScope(
                "生殖能を有する男性・女性への投与上の注意。生殖に関する影響や避妊等の留意事項"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("9.5"),
            title=DefinitionTitle("妊婦"),
            scope=SectionScope(
                "妊婦又は妊娠している可能性のある女性への投与上の注意と、妊娠・胎児への影響"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("9.6"),
            title=DefinitionTitle("授乳婦"),
            scope=SectionScope(
                "授乳婦への投与上の注意。母乳移行や授乳継続・中止等に関する留意事項"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("9.7"),
            title=DefinitionTitle("小児等"),
            scope=SectionScope(
                "小児等への投与上の注意。年齢・発達段階に応じた留意事項と小児等での使用情報"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("9.8"),
            title=DefinitionTitle("高齢者"),
            scope=SectionScope(
                "高齢者への投与上の注意。生理機能等の患者背景に応じた留意事項"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("10"),
            title=DefinitionTitle("相互作用"),
            scope=SectionScope(
                "併用してはいけない、又は併用に注意する薬剤等。併用による臨床症状・措置方法、機序・危険因子"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("10.1"),
            title=DefinitionTitle("併用禁忌"),
            scope=SectionScope(
                "併用してはいけない薬剤等の名称、併用による臨床症状・措置方法、機序・危険因子"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("10.2"),
            title=DefinitionTitle("併用注意"),
            scope=SectionScope(
                "併用に注意する薬剤等の名称、併用による臨床症状・措置方法、機序・危険因子"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("11"),
            title=DefinitionTitle("副作用"),
            scope=SectionScope(
                "投与に伴う副作用。重大な副作用とその他の副作用の種類、症状、発現頻度等"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("11.1"),
            title=DefinitionTitle("重大な副作用"),
            scope=SectionScope(
                "重大な副作用の名称・症状、発現頻度等と、発現時の観察・対応に関する情報"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("11.2"),
            title=DefinitionTitle("その他の副作用"),
            scope=SectionScope(
                "重大な副作用以外の副作用。副作用の種類・症状を発現頻度等で整理した情報と注釈"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("12"),
            title=DefinitionTitle("臨床検査結果に及ぼす影響"),
            scope=SectionScope(
                "薬剤が臨床検査結果の測定・判定に及ぼす影響。検査への干渉等に関する情報"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("13"),
            title=DefinitionTitle("過量投与"),
            scope=SectionScope(
                "過量投与時に現れる症状と、その際に必要となる処置・対応"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("14"),
            title=DefinitionTitle("適用上の注意"),
            scope=SectionScope(
                "調剤・交付・投与・使用時など、製剤を実際に適用する際の注意事項"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("15"),
            title=DefinitionTitle("その他の注意"),
            scope=SectionScope(
                "臨床使用又は非臨床試験に基づく、他の注意事項を補足する情報"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("15.1"),
            title=DefinitionTitle("臨床使用に基づく情報"),
            scope=SectionScope("臨床使用から得られた、他の注意事項を補足する情報"),
        ),
        SectionDefinition(
            code=NumberedSectionCode("15.2"),
            title=DefinitionTitle("非臨床試験に基づく情報"),
            scope=SectionScope(
                "動物実験等の非臨床試験から得られた、他の注意事項を補足する情報"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("16"),
            title=DefinitionTitle("薬物動態"),
            scope=SectionScope(
                "体内での薬物の動き。血中濃度、吸収、分布、代謝、排泄、特定の患者背景や併用による薬物動態の変化"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("16.1"),
            title=DefinitionTitle("血中濃度"),
            scope=SectionScope(
                "投与後の血中濃度の推移と薬物動態パラメータ。最高血中濃度、到達時間、曝露量、半減期等"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("16.2"),
            title=DefinitionTitle("吸収"),
            scope=SectionScope(
                "薬物の体内への吸収に関する情報。吸収の程度・速度や吸収に影響する条件等"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("16.3"),
            title=DefinitionTitle("分布"),
            scope=SectionScope(
                "薬物の体内での分布に関する情報。組織・体液への移行や蛋白結合等"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("16.4"),
            title=DefinitionTitle("代謝"),
            scope=SectionScope(
                "薬物の代謝に関する情報。代謝経路、関与する代謝酵素、代謝物等"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("16.5"),
            title=DefinitionTitle("排泄"),
            scope=SectionScope(
                "薬物の体外への排泄に関する情報。排泄経路、排泄量・割合等"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("16.6"),
            title=DefinitionTitle("特定の背景を有する患者"),
            scope=SectionScope(
                "腎・肝機能障害や年齢等の特定の患者背景による血中濃度・曝露量などの薬物動態への影響"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("16.7"),
            title=DefinitionTitle("薬物相互作用"),
            scope=SectionScope(
                "他の薬剤等との併用による血中濃度・曝露量などの薬物動態への影響と相互作用の試験結果"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("16.8"),
            title=DefinitionTitle("その他"),
            scope=SectionScope(
                "血中濃度・吸収・分布・代謝・排泄・特定の患者背景・薬物相互作用の各項目以外の薬物動態に関する情報"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("17"),
            title=DefinitionTitle("臨床成績"),
            scope=SectionScope(
                "臨床における有効性・安全性の成績。有効性及び安全性の試験、製造販売後調査等の結果"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("17.1"),
            title=DefinitionTitle("有効性及び安全性に関する試験"),
            scope=SectionScope(
                "有効性及び安全性を検討した臨床試験の対象、方法、評価項目と結果"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("17.2"),
            title=DefinitionTitle("製造販売後調査等"),
            scope=SectionScope(
                "製造販売後調査等で得られた使用状況、有効性・安全性等の成績"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("17.3"),
            title=DefinitionTitle("その他"),
            scope=SectionScope(
                "有効性及び安全性に関する試験、製造販売後調査等の各項目以外の臨床成績"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("18"),
            title=DefinitionTitle("薬効薬理"),
            scope=SectionScope("薬効を裏付ける薬理作用と作用機序、薬理試験等の情報"),
        ),
        SectionDefinition(
            code=NumberedSectionCode("18.1"),
            title=DefinitionTitle("作用機序"),
            scope=SectionScope(
                "薬効が生じる作用機序。作用する標的や生体内の過程等の説明"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("19"),
            title=DefinitionTitle("有効成分に関する理化学的知見"),
            scope=SectionScope(
                "有効成分の一般的名称、化学名、分子式・分子量、性状、化学構造式、融点、分配係数、本質、核物理学的特性等"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("20"),
            title=DefinitionTitle("取扱い上の注意"),
            scope=SectionScope(
                "製品を取り扱う際の注意事項。保存・開封後等の製品の取扱いに関する情報"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("21"),
            title=DefinitionTitle("承認条件"),
            scope=SectionScope(
                "医薬品の承認に付された条件と、承認条件として求められる対応"
            ),
        ),
        SectionDefinition(
            code=NumberedSectionCode("22"),
            title=DefinitionTitle("包装"),
            scope=SectionScope("製品の包装形態、包装単位・数量などの包装に関する情報"),
        ),
        SectionDefinition(
            code=NumberedSectionCode("23"),
            title=DefinitionTitle("主要文献"),
            scope=SectionScope("添付文書に引用・参照される主要な文献の情報"),
        ),
        SectionDefinition(
            code=NumberedSectionCode("24"),
            title=DefinitionTitle("文献請求先及び問い合わせ先"),
            scope=SectionScope("文献の請求先及び問い合わせ先の名称、住所、連絡先"),
        ),
        SectionDefinition(
            code=NumberedSectionCode("25"),
            title=DefinitionTitle("保険給付上の注意"),
            scope=SectionScope("保険給付上の取扱いに関する注意事項"),
        ),
        SectionDefinition(
            code=NumberedSectionCode("26"),
            title=DefinitionTitle("製造販売業者等"),
            scope=SectionScope("製造販売業者等の業種別、名称及び住所"),
        ),
    )
)

STANDARD_INTERACTION_COLUMNS = (
    InteractionColumnDefinition(
        id=InteractionColumnId("drug_name"), title=DefinitionTitle("薬剤名")
    ),
    InteractionColumnDefinition(
        id=InteractionColumnId("clinical_symptoms_and_measures"),
        title=DefinitionTitle("臨床症状・措置方法"),
    ),
    InteractionColumnDefinition(
        id=InteractionColumnId("mechanism_and_risk_factors"),
        title=DefinitionTitle("機序・危険因子"),
    ),
)
