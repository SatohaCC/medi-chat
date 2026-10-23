"""XMLの技術タグと添付文書項目を結ぶ型付き定義。名称はDomainから投影する。"""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from backend.domain.attachment.value_objects import (
    InteractionColumnDefinition,
    SectionTaxonomy,
)

from .definition_settings import (
    JanomeMorphologySettings,
    PmdaXmlSettings,
    XmlColumnBinding,
    XmlSectionBinding,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class XmlTagMapping:
    tag: str
    section_code: str


@dataclass(frozen=True, slots=True, kw_only=True)
class XmlContextMapping:
    parent_tag: str
    tag: str
    section_code: str


DEFAULT_XML_TAGS = (
    XmlTagMapping(tag="Warnings", section_code="1"),
    XmlTagMapping(tag="ContraIndications", section_code="2"),
    XmlTagMapping(tag="CompositionAndProperty", section_code="3"),
    XmlTagMapping(tag="Composition", section_code="3.1"),
    XmlTagMapping(tag="Property", section_code="3.2"),
    XmlTagMapping(tag="IndicationsOrEfficacy", section_code="4"),
    XmlTagMapping(tag="EfficacyRelatedPrecautions", section_code="5"),
    XmlTagMapping(tag="InfoDoseAdmin", section_code="6"),
    XmlTagMapping(tag="InfoPrecautionsDosage", section_code="7"),
    XmlTagMapping(tag="ImportantPrecautions", section_code="8"),
    XmlTagMapping(tag="UseInSpecificPopulations", section_code="9"),
    XmlTagMapping(
        tag="UseInPatientsWithComplicationsOrHistoryOfDiseasesEtc", section_code="9.1"
    ),
    XmlTagMapping(tag="PatientsWithRenalImpairment", section_code="9.2"),
    XmlTagMapping(tag="PatientsWithHepaticImpairment", section_code="9.3"),
    XmlTagMapping(tag="MalesAndFemalesOfReproductivePotential", section_code="9.4"),
    XmlTagMapping(tag="UseInPregnant", section_code="9.5"),
    XmlTagMapping(tag="UseInNursing", section_code="9.6"),
    XmlTagMapping(tag="PediatricUse", section_code="9.7"),
    XmlTagMapping(tag="UseInTheElderly", section_code="9.8"),
    XmlTagMapping(tag="Interactions", section_code="10"),
    XmlTagMapping(tag="ContraIndicatedCombinations", section_code="10.1"),
    XmlTagMapping(tag="PrecautionsForCombinations", section_code="10.2"),
    XmlTagMapping(tag="AdverseEvents", section_code="11"),
    XmlTagMapping(tag="SeriousAdverseEvents", section_code="11.1"),
    XmlTagMapping(tag="OtherAdverseEvents", section_code="11.2"),
    XmlTagMapping(tag="InfluenceOnLaboratoryValues", section_code="12"),
    XmlTagMapping(tag="EffectsOnLaboratoryTests", section_code="12"),
    XmlTagMapping(tag="OverDosage", section_code="13"),
    XmlTagMapping(tag="PrecautionsForApplication", section_code="14"),
    XmlTagMapping(tag="OtherPrecautions", section_code="15"),
    XmlTagMapping(tag="InformationBasedOnClinicalUse", section_code="15.1"),
    XmlTagMapping(tag="InformationBasedOnNonClinicalUse", section_code="15.2"),
    XmlTagMapping(tag="Pharmacokinetics", section_code="16"),
    XmlTagMapping(tag="BloodLevel", section_code="16.1"),
    XmlTagMapping(tag="Absorption", section_code="16.2"),
    XmlTagMapping(tag="Distribution", section_code="16.3"),
    XmlTagMapping(tag="Metabolism", section_code="16.4"),
    XmlTagMapping(tag="Excretion", section_code="16.5"),
    XmlTagMapping(tag="SpecificPopulation", section_code="16.6"),
    XmlTagMapping(tag="DrugAndDrugInteractions", section_code="16.7"),
    XmlTagMapping(tag="ResultsOfClinicalTrials", section_code="17"),
    XmlTagMapping(tag="EfficacyAndSafety", section_code="17.1"),
    XmlTagMapping(tag="PostMarketingSurveillance", section_code="17.2"),
    XmlTagMapping(tag="EfficacyPharmacology", section_code="18"),
    XmlTagMapping(tag="MechanismOfAction", section_code="18.1"),
    XmlTagMapping(tag="PhyschemOfActIngredients", section_code="19"),
    XmlTagMapping(tag="PrecautionsForHandling", section_code="20"),
    XmlTagMapping(tag="ConditionsOfApproval", section_code="21"),
    XmlTagMapping(tag="Package", section_code="22"),
    XmlTagMapping(tag="MainLiterature", section_code="23"),
    XmlTagMapping(tag="AddresseeOfLiteratureRequest", section_code="24"),
    XmlTagMapping(tag="AttentionOfInsurance", section_code="25"),
    XmlTagMapping(tag="PrecautionsForInsuranceCoverage", section_code="25"),
    XmlTagMapping(tag="NameAddressManufact", section_code="26"),
)

DEFAULT_XML_CONTEXTS = (
    XmlContextMapping(
        parent_tag="Pharmacokinetics", tag="OtherInformation", section_code="16.8"
    ),
    XmlContextMapping(
        parent_tag="ResultsOfClinicalTrials",
        tag="OtherInformation",
        section_code="17.3",
    ),
)

DEFAULT_COLUMN_TAGS: Mapping[str, str] = MappingProxyType(
    {
        "drug_name": "DrugName",
        "clinical_symptoms_and_measures": "ClinSymptomsAndMeasures",
        "mechanism_and_risk_factors": "MechanismAndRiskFactors",
    }
)
DEFAULT_HEADER_TAGS = frozenset(
    (
        "ApprovalEtc",
        "CompanyIdentifier",
        "DateOfPreparationOrRevision",
        "GenericName",
        "PackageInsertNo",
        "Sccj",
        "TherapeuticClassification",
    )
)
DEFAULT_REFERENCE_TAGS = frozenset(("CommentRef", "HeaderRef", "ReferenceBookRef"))
DEFAULT_ATOMIC_UNITS: Mapping[str, str] = MappingProxyType(
    {
        "Drug": "interaction_row",
        "AdverseReactionDescription": "adverse_reaction_cell",
        "SimpTblRow": "table_row",
        "Reference": "literature_reference",
        "OtherInformation": "other_information",
        "Graphic": "graphic",
    }
)
DEFAULT_MORPHOLOGY_SETTINGS = JanomeMorphologySettings(
    ignored_noun_suffixes=frozenset(
        ("一覧", "事項", "情報", "方法", "注意", "点", "相談", "確認")
    )
)


def build_xml_settings(
    taxonomy: SectionTaxonomy,
    columns: tuple[InteractionColumnDefinition, ...],
    *,
    tags: tuple[XmlTagMapping, ...] = DEFAULT_XML_TAGS,
    contexts: tuple[XmlContextMapping, ...] = DEFAULT_XML_CONTEXTS,
    column_tags: Mapping[str, str] = DEFAULT_COLUMN_TAGS,
) -> PmdaXmlSettings:
    sections = {
        s.code.value: XmlSectionBinding(code=s.code.value, title=s.title.value)
        for s in taxonomy.sections
    }
    if len({m.tag for m in tags}) != len(tags):
        raise ValueError("duplicate XML tag")
    if len({(m.parent_tag, m.tag) for m in contexts}) != len(contexts):
        raise ValueError("duplicate XML context")
    if len({column.id for column in columns}) != len(columns):
        raise ValueError("duplicate interaction column")
    referenced = {mapping.section_code for mapping in tags} | {
        mapping.section_code for mapping in contexts
    }
    if referenced - sections.keys():
        raise ValueError(
            f"unknown XML sections: {sorted(referenced - sections.keys())}"
        )
    if {mapping.tag for mapping in tags} & DEFAULT_HEADER_TAGS:
        raise ValueError("section tags cannot be document headers")
    if any(mapping.parent_tag not in {tag.tag for tag in tags} for mapping in contexts):
        raise ValueError("unknown XML parent tag")
    if {column.id.value for column in columns} - column_tags.keys():
        raise ValueError("missing XML column tag")
    return PmdaXmlSettings(
        sections_by_xml_tag=MappingProxyType(
            {m.tag: sections[m.section_code] for m in tags}
        ),
        sections_by_xml_context=MappingProxyType(
            {(m.parent_tag, m.tag): sections[m.section_code] for m in contexts}
        ),
        interaction_columns=tuple(
            XmlColumnBinding(
                id=c.id.value, title=c.title.value, xml_tag=column_tags[c.id.value]
            )
            for c in columns
        ),
        header_tags=DEFAULT_HEADER_TAGS,
        reference_tags=DEFAULT_REFERENCE_TAGS,
        atomic_units=DEFAULT_ATOMIC_UNITS,
    )
