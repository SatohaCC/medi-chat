"""添付文書の根拠取得・質問解釈の標準方針。IO・SDK非依存。"""

from collections.abc import Mapping
from dataclasses import dataclass, replace
from types import MappingProxyType

from backend.application.indexing.search_values import SearchSectionCode
from backend.domain.foundation.exceptions import DomainValidationError

from .search_models import (
    IntentKeyword,
    IntentPolicy,
    SearchIntentDefinition,
    SymptomKeywordRule,
    TextSearchPolicy,
)
from .search_values import (
    IntentKeywordText,
    IntentName,
    KeywordPriority,
    SearchPolicyTerm,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class EvidenceRetrievalPolicy:
    """質問意図とは独立した、常時参照する項目の方針。"""

    always_retrieved_sections: tuple[SearchSectionCode, ...]

    def __post_init__(self) -> None:
        if len(set(self.always_retrieved_sections)) != len(
            self.always_retrieved_sections
        ):
            raise DomainValidationError("duplicate always-retrieved section")


@dataclass(frozen=True, slots=True, kw_only=True)
class ClassificationRule:
    """質問意図と項目範囲の対応。技術固有のJev形式を含まない。"""

    intent: IntentName
    section_codes: tuple[SearchSectionCode, ...]
    fallback_description: str | None = None

    def __post_init__(self) -> None:
        if len(set(self.section_codes)) != len(self.section_codes):
            raise DomainValidationError("duplicate classification section")
        if not self.section_codes and (
            self.fallback_description is None or not self.fallback_description.strip()
        ):
            raise DomainValidationError(
                "classification without sections requires description"
            )


DEFAULT_RETRIEVAL_POLICY = EvidenceRetrievalPolicy(
    always_retrieved_sections=(
        SearchSectionCode("1"),
        SearchSectionCode("2"),
        SearchSectionCode("8"),
    )
)

DEFAULT_INTENT_POLICY = IntentPolicy(
    intents=(
        SearchIntentDefinition(
            id=IntentName("warnings"),
            section_codes=(SearchSectionCode("1"),),
            keywords=(
                IntentKeyword(
                    text=IntentKeywordText("警告"), exclude_from_text_search=True
                ),
            ),
            keyword_priority=KeywordPriority(13),
        ),
        SearchIntentDefinition(
            id=IntentName("contraindications"),
            section_codes=(SearchSectionCode("2"),),
            keywords=(
                IntentKeyword(
                    text=IntentKeywordText("禁忌"), exclude_from_text_search=True
                ),
            ),
            keyword_priority=KeywordPriority(12),
        ),
        SearchIntentDefinition(
            id=IntentName("composition"),
            section_codes=(SearchSectionCode("3.1"),),
            keywords=(),
            keyword_priority=None,
        ),
        SearchIntentDefinition(
            id=IntentName("appearance"),
            section_codes=(SearchSectionCode("3.2"),),
            keywords=(
                IntentKeyword(
                    text=IntentKeywordText("性状"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("剤形"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("外観"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("色"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("識別コード"), exclude_from_text_search=True
                ),
            ),
            keyword_priority=KeywordPriority(26),
        ),
        SearchIntentDefinition(
            id=IntentName("composition_and_appearance"),
            section_codes=(
                SearchSectionCode("3"),
                SearchSectionCode("3.1"),
                SearchSectionCode("3.2"),
            ),
            keywords=(),
            keyword_priority=None,
        ),
        SearchIntentDefinition(
            id=IntentName("indications"),
            section_codes=(SearchSectionCode("4"), SearchSectionCode("5")),
            keywords=(
                IntentKeyword(
                    text=IntentKeywordText("効能"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("効果"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("何の薬"), exclude_from_text_search=False
                ),
                IntentKeyword(
                    text=IntentKeywordText("どんな薬"), exclude_from_text_search=False
                ),
                IntentKeyword(
                    text=IntentKeywordText("どういう薬"), exclude_from_text_search=False
                ),
                IntentKeyword(
                    text=IntentKeywordText("何に効く"), exclude_from_text_search=False
                ),
                IntentKeyword(
                    text=IntentKeywordText("効く"), exclude_from_text_search=False
                ),
                IntentKeyword(
                    text=IntentKeywordText("効き目"), exclude_from_text_search=False
                ),
                IntentKeyword(
                    text=IntentKeywordText("効きめ"), exclude_from_text_search=False
                ),
                IntentKeyword(
                    text=IntentKeywordText("適応"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("何に使う"), exclude_from_text_search=False
                ),
                IntentKeyword(
                    text=IntentKeywordText("作用"), exclude_from_text_search=True
                ),
            ),
            keyword_priority=KeywordPriority(11),
        ),
        SearchIntentDefinition(
            id=IntentName("precautions_related_to_indications"),
            section_codes=(SearchSectionCode("5"),),
            keywords=(),
            keyword_priority=None,
        ),
        SearchIntentDefinition(
            id=IntentName("dosage"),
            section_codes=(SearchSectionCode("6"), SearchSectionCode("7")),
            keywords=(
                IntentKeyword(
                    text=IntentKeywordText("用法"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("用量"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("飲み方"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("何錠"), exclude_from_text_search=True
                ),
            ),
            keyword_priority=KeywordPriority(3),
        ),
        SearchIntentDefinition(
            id=IntentName("precautions_related_to_dosage"),
            section_codes=(SearchSectionCode("7"),),
            keywords=(),
            keyword_priority=None,
        ),
        SearchIntentDefinition(
            id=IntentName("important_precautions"),
            section_codes=(SearchSectionCode("8"),),
            keywords=(
                IntentKeyword(
                    text=IntentKeywordText("運転"), exclude_from_text_search=False
                ),
                IntentKeyword(
                    text=IntentKeywordText("検査"), exclude_from_text_search=False
                ),
                IntentKeyword(
                    text=IntentKeywordText("基本的注意"), exclude_from_text_search=True
                ),
            ),
            keyword_priority=KeywordPriority(17),
        ),
        SearchIntentDefinition(
            id=IntentName("specific_populations"),
            section_codes=(
                SearchSectionCode("9"),
                SearchSectionCode("9.1"),
                SearchSectionCode("9.2"),
                SearchSectionCode("9.3"),
                SearchSectionCode("9.4"),
                SearchSectionCode("9.5"),
                SearchSectionCode("9.6"),
                SearchSectionCode("9.7"),
                SearchSectionCode("9.8"),
            ),
            keywords=(),
            keyword_priority=None,
        ),
        SearchIntentDefinition(
            id=IntentName("complications_or_history"),
            section_codes=(SearchSectionCode("9.1"),),
            keywords=(),
            keyword_priority=None,
        ),
        SearchIntentDefinition(
            id=IntentName("renal_impairment"),
            section_codes=(SearchSectionCode("9.2"),),
            keywords=(
                IntentKeyword(
                    text=IntentKeywordText("腎"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("透析"), exclude_from_text_search=True
                ),
            ),
            keyword_priority=KeywordPriority(9),
        ),
        SearchIntentDefinition(
            id=IntentName("hepatic_impairment"),
            section_codes=(SearchSectionCode("9.3"),),
            keywords=(
                IntentKeyword(
                    text=IntentKeywordText("肝"), exclude_from_text_search=True
                ),
            ),
            keyword_priority=KeywordPriority(10),
        ),
        SearchIntentDefinition(
            id=IntentName("reproductive_potential"),
            section_codes=(SearchSectionCode("9.4"),),
            keywords=(
                IntentKeyword(
                    text=IntentKeywordText("避妊"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("生殖能"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("妊娠可能"), exclude_from_text_search=False
                ),
            ),
            keyword_priority=KeywordPriority(4),
        ),
        SearchIntentDefinition(
            id=IntentName("pregnancy"),
            section_codes=(SearchSectionCode("9.5"),),
            keywords=(
                IntentKeyword(
                    text=IntentKeywordText("妊婦"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("妊娠"), exclude_from_text_search=True
                ),
            ),
            keyword_priority=KeywordPriority(5),
        ),
        SearchIntentDefinition(
            id=IntentName("nursing"),
            section_codes=(SearchSectionCode("9.6"),),
            keywords=(
                IntentKeyword(
                    text=IntentKeywordText("授乳"), exclude_from_text_search=True
                ),
            ),
            keyword_priority=KeywordPriority(6),
        ),
        SearchIntentDefinition(
            id=IntentName("pediatric"),
            section_codes=(SearchSectionCode("9.7"),),
            keywords=(
                IntentKeyword(
                    text=IntentKeywordText("小児"), exclude_from_text_search=True
                ),
            ),
            keyword_priority=KeywordPriority(7),
        ),
        SearchIntentDefinition(
            id=IntentName("elderly"),
            section_codes=(SearchSectionCode("9.8"),),
            keywords=(
                IntentKeyword(
                    text=IntentKeywordText("高齢"), exclude_from_text_search=True
                ),
            ),
            keyword_priority=KeywordPriority(8),
        ),
        SearchIntentDefinition(
            id=IntentName("interaction"),
            section_codes=(
                SearchSectionCode("10"),
                SearchSectionCode("10.1"),
                SearchSectionCode("10.2"),
                SearchSectionCode("16.7"),
            ),
            keywords=(
                IntentKeyword(
                    text=IntentKeywordText("相互作用"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("飲み合わせ"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("併用"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("一緒に使える"),
                    exclude_from_text_search=True,
                ),
                IntentKeyword(
                    text=IntentKeywordText("一緒に使"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("一緒に飲"), exclude_from_text_search=True
                ),
            ),
            keyword_priority=KeywordPriority(1),
        ),
        SearchIntentDefinition(
            id=IntentName("adverse_events"),
            section_codes=(
                SearchSectionCode("11"),
                SearchSectionCode("11.1"),
                SearchSectionCode("11.2"),
            ),
            keywords=(
                IntentKeyword(
                    text=IntentKeywordText("副作用"), exclude_from_text_search=True
                ),
            ),
            keyword_priority=KeywordPriority(2),
        ),
        SearchIntentDefinition(
            id=IntentName("laboratory_influences"),
            section_codes=(SearchSectionCode("12"),),
            keywords=(),
            keyword_priority=None,
        ),
        SearchIntentDefinition(
            id=IntentName("overdosage"),
            section_codes=(SearchSectionCode("13"),),
            keywords=(
                IntentKeyword(
                    text=IntentKeywordText("過量"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("飲み過ぎ"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("誤飲"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("中毒"), exclude_from_text_search=True
                ),
            ),
            keyword_priority=KeywordPriority(14),
        ),
        SearchIntentDefinition(
            id=IntentName("precautions_for_application"),
            section_codes=(SearchSectionCode("14"),),
            keywords=(
                IntentKeyword(
                    text=IntentKeywordText("適用上"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("粉砕"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("噛み砕"), exclude_from_text_search=True
                ),
            ),
            keyword_priority=KeywordPriority(18),
        ),
        SearchIntentDefinition(
            id=IntentName("other_precautions"),
            section_codes=(
                SearchSectionCode("15"),
                SearchSectionCode("15.1"),
                SearchSectionCode("15.2"),
            ),
            keywords=(),
            keyword_priority=None,
        ),
        SearchIntentDefinition(
            id=IntentName("pharmacokinetics"),
            section_codes=(
                SearchSectionCode("16"),
                SearchSectionCode("16.1"),
                SearchSectionCode("16.2"),
                SearchSectionCode("16.3"),
                SearchSectionCode("16.4"),
                SearchSectionCode("16.5"),
                SearchSectionCode("16.6"),
                SearchSectionCode("16.7"),
                SearchSectionCode("16.8"),
            ),
            keywords=(
                IntentKeyword(
                    text=IntentKeywordText("動態"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("血中濃度"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("半減期"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("代謝"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("排泄"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("CYP"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("バイオアベイラビリティ"),
                    exclude_from_text_search=True,
                ),
            ),
            keyword_priority=KeywordPriority(15),
        ),
        SearchIntentDefinition(
            id=IntentName("clinical_studies"),
            section_codes=(
                SearchSectionCode("17"),
                SearchSectionCode("17.1"),
                SearchSectionCode("17.2"),
                SearchSectionCode("17.3"),
            ),
            keywords=(
                IntentKeyword(
                    text=IntentKeywordText("臨床成績"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("治験"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("有効率"), exclude_from_text_search=True
                ),
            ),
            keyword_priority=KeywordPriority(19),
        ),
        SearchIntentDefinition(
            id=IntentName("pharmacology"),
            section_codes=(SearchSectionCode("18"), SearchSectionCode("18.1")),
            keywords=(
                IntentKeyword(
                    text=IntentKeywordText("薬理"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("機序"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("メカニズム"), exclude_from_text_search=False
                ),
            ),
            keyword_priority=KeywordPriority(16),
        ),
        SearchIntentDefinition(
            id=IntentName("physicochemical_properties"),
            section_codes=(SearchSectionCode("19"),),
            keywords=(
                IntentKeyword(
                    text=IntentKeywordText("理化学"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("構造式"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("分子量"), exclude_from_text_search=True
                ),
            ),
            keyword_priority=KeywordPriority(21),
        ),
        SearchIntentDefinition(
            id=IntentName("storage_and_handling"),
            section_codes=(SearchSectionCode("20"),),
            keywords=(
                IntentKeyword(
                    text=IntentKeywordText("保存"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("保管"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("取扱い"), exclude_from_text_search=True
                ),
            ),
            keyword_priority=KeywordPriority(25),
        ),
        SearchIntentDefinition(
            id=IntentName("conditions_of_approval"),
            section_codes=(SearchSectionCode("21"),),
            keywords=(
                IntentKeyword(
                    text=IntentKeywordText("承認条件"), exclude_from_text_search=True
                ),
            ),
            keyword_priority=KeywordPriority(23),
        ),
        SearchIntentDefinition(
            id=IntentName("packaging"),
            section_codes=(SearchSectionCode("22"),),
            keywords=(
                IntentKeyword(
                    text=IntentKeywordText("包装"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("PTP"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("シート"), exclude_from_text_search=True
                ),
            ),
            keyword_priority=KeywordPriority(20),
        ),
        SearchIntentDefinition(
            id=IntentName("literature"),
            section_codes=(SearchSectionCode("23"),),
            keywords=(),
            keyword_priority=None,
        ),
        SearchIntentDefinition(
            id=IntentName("contact_info"),
            section_codes=(SearchSectionCode("24"),),
            keywords=(
                IntentKeyword(
                    text=IntentKeywordText("文献"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("問い合わせ"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("相談窓口"), exclude_from_text_search=True
                ),
            ),
            keyword_priority=KeywordPriority(22),
        ),
        SearchIntentDefinition(
            id=IntentName("insurance_benefits"),
            section_codes=(SearchSectionCode("25"),),
            keywords=(),
            keyword_priority=None,
        ),
        SearchIntentDefinition(
            id=IntentName("manufacturer_info"),
            section_codes=(SearchSectionCode("26"),),
            keywords=(
                IntentKeyword(
                    text=IntentKeywordText("製造販売"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("メーカー"), exclude_from_text_search=True
                ),
                IntentKeyword(
                    text=IntentKeywordText("製薬会社"), exclude_from_text_search=True
                ),
            ),
            keyword_priority=KeywordPriority(24),
        ),
        SearchIntentDefinition(
            id=IntentName("general_or_other"),
            section_codes=(),
            keywords=(),
            keyword_priority=None,
        ),
        SearchIntentDefinition(
            id=IntentName("document_search"),
            section_codes=(),
            keywords=(),
            keyword_priority=None,
        ),
    ),
    fallback_intent=IntentName("document_search"),
    general_intent=IntentName("general_or_other"),
)

DEFAULT_CLASSIFICATION_RULES = (
    ClassificationRule(
        intent=IntentName("warnings"), section_codes=(SearchSectionCode("1"),)
    ),
    ClassificationRule(
        intent=IntentName("contraindications"), section_codes=(SearchSectionCode("2"),)
    ),
    ClassificationRule(
        intent=IntentName("composition"), section_codes=(SearchSectionCode("3.1"),)
    ),
    ClassificationRule(
        intent=IntentName("appearance"), section_codes=(SearchSectionCode("3.2"),)
    ),
    ClassificationRule(
        intent=IntentName("indications"),
        section_codes=(SearchSectionCode("4"), SearchSectionCode("5")),
    ),
    ClassificationRule(
        intent=IntentName("dosage"),
        section_codes=(SearchSectionCode("6"), SearchSectionCode("7")),
    ),
    ClassificationRule(
        intent=IntentName("important_precautions"),
        section_codes=(SearchSectionCode("8"),),
    ),
    ClassificationRule(
        intent=IntentName("complications_or_history"),
        section_codes=(SearchSectionCode("9.1"),),
    ),
    ClassificationRule(
        intent=IntentName("renal_impairment"), section_codes=(SearchSectionCode("9.2"),)
    ),
    ClassificationRule(
        intent=IntentName("hepatic_impairment"),
        section_codes=(SearchSectionCode("9.3"),),
    ),
    ClassificationRule(
        intent=IntentName("reproductive_potential"),
        section_codes=(SearchSectionCode("9.4"),),
    ),
    ClassificationRule(
        intent=IntentName("pregnancy"), section_codes=(SearchSectionCode("9.5"),)
    ),
    ClassificationRule(
        intent=IntentName("nursing"), section_codes=(SearchSectionCode("9.6"),)
    ),
    ClassificationRule(
        intent=IntentName("pediatric"), section_codes=(SearchSectionCode("9.7"),)
    ),
    ClassificationRule(
        intent=IntentName("elderly"), section_codes=(SearchSectionCode("9.8"),)
    ),
    ClassificationRule(
        intent=IntentName("interaction"), section_codes=(SearchSectionCode("10"),)
    ),
    ClassificationRule(
        intent=IntentName("adverse_events"), section_codes=(SearchSectionCode("11"),)
    ),
    ClassificationRule(
        intent=IntentName("laboratory_influences"),
        section_codes=(SearchSectionCode("12"),),
    ),
    ClassificationRule(
        intent=IntentName("overdosage"), section_codes=(SearchSectionCode("13"),)
    ),
    ClassificationRule(
        intent=IntentName("precautions_for_application"),
        section_codes=(SearchSectionCode("14"),),
    ),
    ClassificationRule(
        intent=IntentName("other_precautions"), section_codes=(SearchSectionCode("15"),)
    ),
    ClassificationRule(
        intent=IntentName("pharmacokinetics"), section_codes=(SearchSectionCode("16"),)
    ),
    ClassificationRule(
        intent=IntentName("clinical_studies"), section_codes=(SearchSectionCode("17"),)
    ),
    ClassificationRule(
        intent=IntentName("pharmacology"), section_codes=(SearchSectionCode("18"),)
    ),
    ClassificationRule(
        intent=IntentName("physicochemical_properties"),
        section_codes=(SearchSectionCode("19"),),
    ),
    ClassificationRule(
        intent=IntentName("storage_and_handling"),
        section_codes=(SearchSectionCode("20"),),
    ),
    ClassificationRule(
        intent=IntentName("conditions_of_approval"),
        section_codes=(SearchSectionCode("21"),),
    ),
    ClassificationRule(
        intent=IntentName("packaging"), section_codes=(SearchSectionCode("22"),)
    ),
    ClassificationRule(
        intent=IntentName("literature"), section_codes=(SearchSectionCode("23"),)
    ),
    ClassificationRule(
        intent=IntentName("contact_info"), section_codes=(SearchSectionCode("24"),)
    ),
    ClassificationRule(
        intent=IntentName("insurance_benefits"),
        section_codes=(SearchSectionCode("25"),),
    ),
    ClassificationRule(
        intent=IntentName("manufacturer_info"), section_codes=(SearchSectionCode("26"),)
    ),
    ClassificationRule(
        intent=IntentName("general_or_other"),
        section_codes=(),
        fallback_description="上記いずれにも該当しない質問、雑談、一般的な質問",
    ),
)

DEFAULT_DISPLAY_TITLES: Mapping[str, str] = MappingProxyType(
    {
        "3.2": "性状",
        "9.1": "合併症・既往歴等",
        "9.2": "腎機能障害",
        "9.3": "肝機能障害",
        "19": "理化学的知見",
        "24": "文献請求先・問い合わせ先",
    }
)

DEFAULT_CLASSIFICATION_TITLES: Mapping[str, str] = MappingProxyType(
    {"4": "効能・効果", "6": "用法・用量", "24": "文献請求先・問い合わせ先"}
)

DEFAULT_ADDITIONAL_STOP_WORDS = frozenset(
    (
        SearchPolicyTerm("g"),
        SearchPolicyTerm("kg"),
        SearchPolicyTerm("mL"),
        SearchPolicyTerm("mcg"),
        SearchPolicyTerm("mg"),
        SearchPolicyTerm("ml"),
        SearchPolicyTerm("μg"),
        SearchPolicyTerm("こと"),
        SearchPolicyTerm("ため"),
        SearchPolicyTerm("とき"),
        SearchPolicyTerm("どう"),
        SearchPolicyTerm("どこ"),
        SearchPolicyTerm("どれ"),
        SearchPolicyTerm("について"),
        SearchPolicyTerm("もの"),
        SearchPolicyTerm("カプセル"),
        SearchPolicyTerm("カプセル剤"),
        SearchPolicyTerm("クリーム"),
        SearchPolicyTerm("シロップ"),
        SearchPolicyTerm("テープ"),
        SearchPolicyTerm("一緒"),
        SearchPolicyTerm("一覧"),
        SearchPolicyTerm("主要文献"),
        SearchPolicyTerm("乳児"),
        SearchPolicyTerm("以前"),
        SearchPolicyTerm("以降"),
        SearchPolicyTerm("何"),
        SearchPolicyTerm("作用機序"),
        SearchPolicyTerm("併用注意"),
        SearchPolicyTerm("併用禁忌"),
        SearchPolicyTerm("保険"),
        SearchPolicyTerm("保険給付上の注意"),
        SearchPolicyTerm("前後"),
        SearchPolicyTerm("医薬品"),
        SearchPolicyTerm("単位"),
        SearchPolicyTerm("取扱"),
        SearchPolicyTerm("可能性"),
        SearchPolicyTerm("基準"),
        SearchPolicyTerm("場合"),
        SearchPolicyTerm("大丈夫"),
        SearchPolicyTerm("女性"),
        SearchPolicyTerm("対処"),
        SearchPolicyTerm("平気"),
        SearchPolicyTerm("幼児"),
        SearchPolicyTerm("影響"),
        SearchPolicyTerm("情報"),
        SearchPolicyTerm("投与"),
        SearchPolicyTerm("授乳婦"),
        SearchPolicyTerm("教えて"),
        SearchPolicyTerm("散"),
        SearchPolicyTerm("文献請求先"),
        SearchPolicyTerm("新生児"),
        SearchPolicyTerm("方法"),
        SearchPolicyTerm("時"),
        SearchPolicyTerm("有害事象"),
        SearchPolicyTerm("服用"),
        SearchPolicyTerm("注射"),
        SearchPolicyTerm("注意"),
        SearchPolicyTerm("注意点"),
        SearchPolicyTerm("添付文書"),
        SearchPolicyTerm("点滴"),
        SearchPolicyTerm("男性"),
        SearchPolicyTerm("相互"),
        SearchPolicyTerm("相談"),
        SearchPolicyTerm("確認"),
        SearchPolicyTerm("程度"),
        SearchPolicyTerm("組成"),
        SearchPolicyTerm("肝機能障害"),
        SearchPolicyTerm("肝臓"),
        SearchPolicyTerm("肝障害"),
        SearchPolicyTerm("腎機能障害"),
        SearchPolicyTerm("腎臓"),
        SearchPolicyTerm("腎障害"),
        SearchPolicyTerm("薬"),
        SearchPolicyTerm("薬剤"),
        SearchPolicyTerm("記載"),
        SearchPolicyTerm("誰"),
        SearchPolicyTerm("質問"),
        SearchPolicyTerm("軟膏"),
        SearchPolicyTerm("過量投与"),
        SearchPolicyTerm("適用上の注意"),
        SearchPolicyTerm("錠"),
        SearchPolicyTerm("錠剤"),
        SearchPolicyTerm("関連"),
        SearchPolicyTerm("飲む"),
        SearchPolicyTerm("高齢者"),
    )
)

DEFAULT_TEXT_SEARCH_POLICY = TextSearchPolicy(
    stop_words=DEFAULT_ADDITIONAL_STOP_WORDS
    | frozenset(
        SearchPolicyTerm(keyword.text.value)
        for intent in DEFAULT_INTENT_POLICY.intents
        for keyword in intent.keywords
        if keyword.exclude_from_text_search
    ),
    symptom_rules=(
        SymptomKeywordRule(
            adjective=SearchPolicyTerm("眠い"),
            keywords=(SearchPolicyTerm("眠気"), SearchPolicyTerm("傾眠")),
        ),
        SymptomKeywordRule(
            adjective=SearchPolicyTerm("痒い"),
            keywords=(SearchPolicyTerm("そう痒"), SearchPolicyTerm("かゆみ")),
        ),
        SymptomKeywordRule(
            adjective=SearchPolicyTerm("かゆい"),
            keywords=(SearchPolicyTerm("そう痒"), SearchPolicyTerm("かゆみ")),
        ),
        SymptomKeywordRule(
            adjective=SearchPolicyTerm("だるい"),
            keywords=(SearchPolicyTerm("倦怠感"), SearchPolicyTerm("倦怠")),
        ),
        SymptomKeywordRule(
            adjective=SearchPolicyTerm("痛い"),
            keywords=(
                SearchPolicyTerm("疼痛"),
                SearchPolicyTerm("痛み"),
                SearchPolicyTerm("痛"),
            ),
        ),
        SymptomKeywordRule(
            adjective=SearchPolicyTerm("苦い"), keywords=(SearchPolicyTerm("苦味"),)
        ),
        SymptomKeywordRule(
            adjective=SearchPolicyTerm("重い"),
            keywords=(SearchPolicyTerm("重感"), SearchPolicyTerm("不快感")),
        ),
    ),
    scope_heading_texts=frozenset(
        (
            SearchPolicyTerm("成人"),
            SearchPolicyTerm("小児"),
            SearchPolicyTerm("〈効能共通〉"),
        )
    ),
)


def build_text_search_policy(intent_policy: IntentPolicy) -> TextSearchPolicy:
    return replace(
        DEFAULT_TEXT_SEARCH_POLICY,
        stop_words=DEFAULT_ADDITIONAL_STOP_WORDS
        | frozenset(
            SearchPolicyTerm(keyword.text.value)
            for intent in intent_policy.intents
            for keyword in intent.keywords
            if keyword.exclude_from_text_search
        ),
    )
