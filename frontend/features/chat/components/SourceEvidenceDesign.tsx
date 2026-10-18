"use client";

import { defineCatalog } from "@json-render/core";
import { defineRegistry, JSONUIProvider, Renderer, schema } from "@json-render/react";
import type { StyleXStyles } from "@stylexjs/stylex";
import * as stylex from "@stylexjs/stylex";
import { z } from "zod";
import type { SourceItem } from "../model/chat";
import {
  buildSourceEvidenceSpec,
  type EvidenceDesign,
} from "../model/sourceEvidenceSpec";
import { HighlightText } from "./HighlightText";
import { SourceEvidenceContent } from "./SourceEvidenceContent";
import { styles } from "./SourceEvidenceDesign.styles";

const evidenceProps = z.object({
  content: z.string(),
  columns: z.record(z.string(), z.string()),
  highlightWords: z.array(z.string()),
});

const catalog = defineCatalog(schema, {
  components: {
    WarningEvidence: { props: evidenceProps, description: "添文の警告の原文" },
    ContraindicationEvidence: { props: evidenceProps, description: "添文の禁忌の原文" },
    CompositionPropertyEvidence: { props: evidenceProps, description: "添文の組成・性状の原文" },
    DosageEvidence: { props: evidenceProps, description: "添文の用法・用量の原文" },
    PrecautionEvidence: { props: evidenceProps, description: "添文の注意事項の原文" },
    SpecificPopulationEvidence: { props: evidenceProps, description: "添文の特定背景患者の原文" },
    InteractionEvidence: { props: evidenceProps, description: "添文の相互作用の原文" },
    AdverseReactionEvidence: { props: evidenceProps, description: "添文の副作用の原文" },
    OverdosageEvidence: { props: evidenceProps, description: "添文の過量投与の原文" },
    PharmacokineticsEvidence: { props: evidenceProps, description: "添文の薬物動態の原文" },
    ClinicalStudiesEvidence: { props: evidenceProps, description: "添文の臨床成績の原文" },
    PharmacologyEvidence: { props: evidenceProps, description: "添文の薬効薬理の原文" },
    PhysicochemicalEvidence: { props: evidenceProps, description: "添文の理化学的知見の原文" },
    HandlingPackagingEvidence: { props: evidenceProps, description: "添文の取扱い・包装の原文" },
    ReferenceEvidence: { props: evidenceProps, description: "添文の主要文献の原文" },
    TextEvidence: { props: evidenceProps, description: "添文の原文" },
  },
  actions: {},
});

const columnLabels: Record<string, string> = {
  drug_name: "薬剤名等（原文）",
  clinical_symptoms_and_measures: "臨床症状・措置方法（原文）",
  mechanism_and_risk_factors: "機序・危険因子（原文）",
};

const headings: Record<EvidenceDesign, string> = {
  WarningEvidence: "警告（原文）",
  ContraindicationEvidence: "禁忌（原文）",
  CompositionPropertyEvidence: "組成・性状（原文）",
  DosageEvidence: "用法・用量と関連する注意（原文）",
  PrecautionEvidence: "適用・使用上の注意（原文）",
  SpecificPopulationEvidence: "特定の背景を有する患者に関する注意（原文）",
  InteractionEvidence: "添文の相互作用記載",
  AdverseReactionEvidence: "副作用（原文）",
  OverdosageEvidence: "過量投与（原文）",
  PharmacokineticsEvidence: "薬物動態（原文）",
  ClinicalStudiesEvidence: "臨床成績（原文）",
  PharmacologyEvidence: "薬効薬理（原文）",
  PhysicochemicalEvidence: "有効成分に関する理化学的知見（原文）",
  HandlingPackagingEvidence: "取扱い上の注意・包装（原文）",
  ReferenceEvidence: "主要文献（原文）",
  TextEvidence: "添文の記載（原文）",
};

const designStyles: Record<EvidenceDesign, StyleXStyles | null | undefined> = {
  WarningEvidence: styles.warning,
  ContraindicationEvidence: styles.contraindication,
  CompositionPropertyEvidence: styles.compositionProperty,
  DosageEvidence: styles.dosage,
  PrecautionEvidence: styles.precaution,
  SpecificPopulationEvidence: styles.specificPopulation,
  InteractionEvidence: styles.interaction,
  AdverseReactionEvidence: styles.adverseReaction,
  OverdosageEvidence: styles.overdosage,
  PharmacokineticsEvidence: styles.pharmacokinetics,
  ClinicalStudiesEvidence: styles.clinicalStudies,
  PharmacologyEvidence: styles.pharmacology,
  PhysicochemicalEvidence: styles.physicochemical,
  HandlingPackagingEvidence: styles.handlingPackaging,
  ReferenceEvidence: styles.reference,
  TextEvidence: null,
};

function EvidenceBody({
  design,
  content,
  columns,
  highlightWords,
}: z.infer<typeof evidenceProps> & {
  design: EvidenceDesign;
  highlightWords?: string[];
}) {
  const entries = Object.entries(columns).filter(([, value]) => value.trim());
  return (
    <section
      data-evidence-design={design}
      aria-label={headings[design]}
      {...stylex.props(styles.body, designStyles[design])}
    >
      <h4 {...stylex.props(styles.heading)}>{headings[design]}</h4>
      {entries.length > 0 ? (
        <>
          <div {...stylex.props(styles.tableContainer)}>
            <table {...stylex.props(styles.table)}>
              <thead>
                <tr>
                  {entries.map(([key]) => (
                    <th key={key} scope="col" {...stylex.props(styles.label)}>
                      {columnLabels[key] ?? key}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr>
                  {entries.map(([key, value]) => (
                    <td key={key} {...stylex.props(styles.value)}>
                      <HighlightText text={value} words={highlightWords} />
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
          {content && (
            <details {...stylex.props(styles.original)}>
              <summary {...stylex.props(styles.summary)}>原文全体・注記を表示</summary>
              <SourceEvidenceContent content={content} highlightWords={highlightWords} />
            </details>
          )}
        </>
      ) : (
        <SourceEvidenceContent content={content} highlightWords={highlightWords} />
      )}
    </section>
  );
}

const { registry } = defineRegistry(catalog, {
  components: {
    WarningEvidence: ({ props }) => (
      <EvidenceBody {...props} design="WarningEvidence" />
    ),
    ContraindicationEvidence: ({ props }) => (
      <EvidenceBody {...props} design="ContraindicationEvidence" />
    ),
    CompositionPropertyEvidence: ({ props }) => (
      <EvidenceBody {...props} design="CompositionPropertyEvidence" />
    ),
    DosageEvidence: ({ props }) => <EvidenceBody {...props} design="DosageEvidence" />,
    PrecautionEvidence: ({ props }) => (
      <EvidenceBody {...props} design="PrecautionEvidence" />
    ),
    SpecificPopulationEvidence: ({ props }) => (
      <EvidenceBody {...props} design="SpecificPopulationEvidence" />
    ),
    InteractionEvidence: ({ props }) => (
      <EvidenceBody {...props} design="InteractionEvidence" />
    ),
    AdverseReactionEvidence: ({ props }) => (
      <EvidenceBody {...props} design="AdverseReactionEvidence" />
    ),
    OverdosageEvidence: ({ props }) => (
      <EvidenceBody {...props} design="OverdosageEvidence" />
    ),
    PharmacokineticsEvidence: ({ props }) => (
      <EvidenceBody {...props} design="PharmacokineticsEvidence" />
    ),
    ClinicalStudiesEvidence: ({ props }) => (
      <EvidenceBody {...props} design="ClinicalStudiesEvidence" />
    ),
    PharmacologyEvidence: ({ props }) => (
      <EvidenceBody {...props} design="PharmacologyEvidence" />
    ),
    PhysicochemicalEvidence: ({ props }) => (
      <EvidenceBody {...props} design="PhysicochemicalEvidence" />
    ),
    HandlingPackagingEvidence: ({ props }) => (
      <EvidenceBody {...props} design="HandlingPackagingEvidence" />
    ),
    ReferenceEvidence: ({ props }) => (
      <EvidenceBody {...props} design="ReferenceEvidence" />
    ),
    TextEvidence: ({ props }) => <EvidenceBody {...props} design="TextEvidence" />,
  },
});

// All props come from retrieved evidence. No server-supplied UI or model-generated actions.
export function SourceEvidenceDesign({
  source,
  highlightWords,
}: {
  source: SourceItem;
  highlightWords?: string[];
}) {
  return (
    <JSONUIProvider registry={registry}>
      <Renderer
        spec={buildSourceEvidenceSpec(source, highlightWords)}
        registry={registry}
      />
    </JSONUIProvider>
  );
}
