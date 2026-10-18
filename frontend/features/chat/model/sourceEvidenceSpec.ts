import type { Spec } from "@json-render/core";
import type { SourceItem } from "./chat";

export type EvidenceDesign =
  | "WarningEvidence"
  | "ContraindicationEvidence"
  | "CompositionPropertyEvidence"
  | "DosageEvidence"
  | "PrecautionEvidence"
  | "SpecificPopulationEvidence"
  | "InteractionEvidence"
  | "AdverseReactionEvidence"
  | "OverdosageEvidence"
  | "PharmacokineticsEvidence"
  | "ClinicalStudiesEvidence"
  | "PharmacologyEvidence"
  | "PhysicochemicalEvidence"
  | "HandlingPackagingEvidence"
  | "ReferenceEvidence"
  | "TextEvidence";

function isSection(code: string, parent: string): boolean {
  return code === parent || code.startsWith(`${parent}.`);
}

// Select a presentation from source structure, never infer a clinical judgment.
export function evidenceDesign(source: SourceItem): EvidenceDesign {
  const code = source.section.code.trim();
  if (isSection(code, "1")) return "WarningEvidence";
  if (isSection(code, "2")) return "ContraindicationEvidence";
  if (isSection(code, "3")) return "CompositionPropertyEvidence";
  if (source.kind === "interaction_row" || isSection(code, "10")) {
    return "InteractionEvidence";
  }
  if (isSection(code, "6") || isSection(code, "7")) return "DosageEvidence";
  if (isSection(code, "8") || isSection(code, "14")) return "PrecautionEvidence";
  if (isSection(code, "9")) return "SpecificPopulationEvidence";
  if (isSection(code, "11")) return "AdverseReactionEvidence";
  if (isSection(code, "13")) return "OverdosageEvidence";
  if (isSection(code, "16")) return "PharmacokineticsEvidence";
  if (isSection(code, "17")) return "ClinicalStudiesEvidence";
  if (isSection(code, "18")) return "PharmacologyEvidence";
  if (isSection(code, "19")) return "PhysicochemicalEvidence";
  if (isSection(code, "20") || isSection(code, "21") || isSection(code, "22")) {
    return "HandlingPackagingEvidence";
  }
  if (isSection(code, "23")) return "ReferenceEvidence";
  return "TextEvidence";
}

export function buildSourceEvidenceSpec(
  source: SourceItem,
  highlightWords: string[] = [],
): Spec {
  return {
    root: "evidence",
    elements: {
      evidence: {
        type: evidenceDesign(source),
        props: {
          content: source.excerpt,
          columns: source.columns ?? {},
          highlightWords,
        },
        children: [],
      },
    },
  };
}
