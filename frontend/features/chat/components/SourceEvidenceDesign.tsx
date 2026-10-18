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
import { ExpandableEvidenceContent } from "./ExpandableEvidenceContent";
import { SourceEvidenceContent } from "./SourceEvidenceContent";
import { styles } from "./SourceEvidenceDesign.styles";

const evidenceProps = z.object({
  content: z.string(),
  columns: z.record(z.string(), z.string()),
  highlightWords: z.array(z.string()),
});

const catalog = defineCatalog(schema, {
  components: {
    WarningEvidence: { props: evidenceProps, description: "添文の警告" },
    ContraindicationEvidence: { props: evidenceProps, description: "添文の禁忌" },
    CompositionPropertyEvidence: { props: evidenceProps, description: "添文の組成・性状" },
    DosageEvidence: { props: evidenceProps, description: "添文の用法・用量" },
    PrecautionEvidence: { props: evidenceProps, description: "添文の注意事項" },
    SpecificPopulationEvidence: { props: evidenceProps, description: "添文の特定背景患者" },
    InteractionEvidence: { props: evidenceProps, description: "添文の相互作用" },
    AdverseReactionEvidence: { props: evidenceProps, description: "添文の副作用" },
    OverdosageEvidence: { props: evidenceProps, description: "添文の過量投与" },
    PharmacokineticsEvidence: { props: evidenceProps, description: "添文の薬物動態" },
    ClinicalStudiesEvidence: { props: evidenceProps, description: "添文の臨床成績" },
    PharmacologyEvidence: { props: evidenceProps, description: "添文の薬効薬理" },
    PhysicochemicalEvidence: { props: evidenceProps, description: "添文の理化学的知見" },
    HandlingPackagingEvidence: { props: evidenceProps, description: "添文の取扱い・包装" },
    ReferenceEvidence: { props: evidenceProps, description: "添文の主要文献" },
    TextEvidence: { props: evidenceProps, description: "添文の記載" },
  },
  actions: {},
});

const columnLabels: Record<string, string> = {
  drug_name: "薬剤名等",
  clinical_symptoms_and_measures: "臨床症状・措置方法",
  mechanism_and_risk_factors: "機序・危険因子",
};

const headings: Record<EvidenceDesign, string> = {
  WarningEvidence: "警告",
  ContraindicationEvidence: "禁忌",
  CompositionPropertyEvidence: "組成・性状",
  DosageEvidence: "用法・用量と関連する注意",
  PrecautionEvidence: "適用・使用上の注意",
  SpecificPopulationEvidence: "特定の背景を有する患者に関する注意",
  InteractionEvidence: "相互作用",
  AdverseReactionEvidence: "副作用",
  OverdosageEvidence: "過量投与",
  PharmacokineticsEvidence: "薬物動態",
  ClinicalStudiesEvidence: "臨床成績",
  PharmacologyEvidence: "薬効薬理",
  PhysicochemicalEvidence: "有効成分に関する理化学的知見",
  HandlingPackagingEvidence: "取扱い上の注意・包装",
  ReferenceEvidence: "主要文献",
  TextEvidence: "添文の記載",
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
  const isAlwaysExpanded =
    design === "WarningEvidence" || design === "ContraindicationEvidence";
  const entries = Object.entries(columns).filter(([, value]) => value.trim());
  return (
    <section
      data-evidence-design={design}
      aria-label={headings[design]}
      {...stylex.props(styles.body, designStyles[design])}
    >
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
              <summary {...stylex.props(styles.summary)}>注記・全文を表示</summary>
              <SourceEvidenceContent content={content} highlightWords={highlightWords} />
            </details>
          )}
        </>
      ) : (
        <ExpandableEvidenceContent
          content={content}
          highlightWords={highlightWords}
          alwaysExpanded={isAlwaysExpanded}
        />
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
