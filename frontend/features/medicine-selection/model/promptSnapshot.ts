export interface SelectedMedicineItem {
  yj_code: string;
  name: string;
  standard?: string | null;
  unit?: string | null;
}

export interface PromptSegmentLike {
  type: string;
  text?: string;
  value?: unknown;
}

export interface PromptLike {
  segments: readonly PromptSegmentLike[];
}

/**
 * Deduplicates medicines by yj_code, preserving the first appearance.
 */
export function deduplicateMedicines(
  medicines: readonly SelectedMedicineItem[],
): SelectedMedicineItem[] {
  const seen = new Set<string>();
  const result: SelectedMedicineItem[] = [];
  for (const med of medicines) {
    if (!med.yj_code || seen.has(med.yj_code)) continue;
    seen.add(med.yj_code);
    result.push(med);
  }
  return result;
}

/**
 * Extracts mentions from token segments with custom medicine data.
 */
export function extractMentionsFromSegments(
  segments: readonly PromptSegmentLike[],
): SelectedMedicineItem[] {
  const extracted: SelectedMedicineItem[] = [];
  for (const segment of segments) {
    if (segment.type === "token") {
      const val = segment.value as
        | { type?: string; valueType?: string; data?: unknown }
        | undefined;
      if (
        val &&
        val.type === "custom" &&
        val.valueType === "medicine" &&
        val.data &&
        typeof val.data === "object"
      ) {
        const data = val.data as Partial<SelectedMedicineItem>;
        if (data.yj_code && data.name) {
          const item: SelectedMedicineItem = {
            yj_code: data.yj_code,
            name: data.name,
          };
          if (data.standard !== undefined) item.standard = data.standard;
          if (data.unit !== undefined) item.unit = data.unit;
          extracted.push(item);
        }
      }
    }
  }
  return deduplicateMedicines(extracted);
}

/**
 * Serializes prompt segments to content string, formatting medicine tokens as `@薬品名`.
 */
export function buildPayloadContent(
  segmentsOrPrompt: readonly PromptSegmentLike[] | PromptLike,
): string {
  const segments: readonly PromptSegmentLike[] =
    "segments" in segmentsOrPrompt ? segmentsOrPrompt.segments : segmentsOrPrompt;

  return segments
    .map((seg: PromptSegmentLike) => {
      if (seg.type === "token") {
        const val = seg.value as { type?: string; url?: string } | undefined;
        if (val?.type === "url" && val.url) {
          return val.url;
        }
        const text = seg.text ?? "";
        return text.startsWith("@") ? text : `@${text}`;
      }
      return seg.text ?? "";
    })
    .join("");
}

export interface TargetMedicinesInput {
  baseline: readonly SelectedMedicineItem[];
  persistentAdditional: readonly SelectedMedicineItem[];
  mentions: readonly SelectedMedicineItem[];
}

export interface TargetMedicinesState {
  target: SelectedMedicineItem[];
  additional: SelectedMedicineItem[];
  canSend: boolean;
}

/**
 * Computes Target medicines T and Additional medicines (T \ B) according to state transition rules.
 * If mentions M is present: T = unique(B + M)
 * If mentions M is empty:   T = unique(B + C)
 */
export function computeTargetMedicines({
  baseline,
  persistentAdditional,
  mentions,
}: TargetMedicinesInput): TargetMedicinesState {
  const deduplicatedBaseline = deduplicateMedicines(baseline);
  const deduplicatedMentions = deduplicateMedicines(mentions);
  const deduplicatedPersistent = deduplicateMedicines(persistentAdditional);

  let target: SelectedMedicineItem[];

  if (deduplicatedMentions.length > 0) {
    target = deduplicateMedicines([...deduplicatedBaseline, ...deduplicatedMentions]);
  } else {
    target = deduplicateMedicines([...deduplicatedBaseline, ...deduplicatedPersistent]);
  }

  const baselineYjSet = new Set(deduplicatedBaseline.map((b) => b.yj_code));
  const additional = target.filter((item) => !baselineYjSet.has(item.yj_code));
  const canSend = target.length > 0;

  return {
    target,
    additional,
    canSend,
  };
}

export interface PostSendState {
  baseline: SelectedMedicineItem[];
  persistentAdditional: SelectedMedicineItem[];
}

/**
 * Resolves post-send state: baseline is preserved, persistentAdditional is set to additional (T \ B).
 */
export function resolvePostSendState(state: TargetMedicinesState): PostSendState {
  const additionalYjSet = new Set(state.additional.map((a) => a.yj_code));
  return {
    baseline: state.target.filter((t) => !additionalYjSet.has(t.yj_code)),
    persistentAdditional: [...state.additional],
  };
}
