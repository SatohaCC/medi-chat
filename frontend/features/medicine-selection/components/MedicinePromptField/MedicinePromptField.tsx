"use client";
import { useCallback } from "react";
import {
  type PromptDocument,
  TokenPromptInput,
} from "../../../../shared/component/TokenPromptInput";
import { type MedicineEntry, searchMedicines } from "../../model/medicineAutocomplete";
import { buildPayloadContent } from "../../model/promptSnapshot";
export interface MedicinePromptFieldProps {
  maxLength: number;
  value: PromptDocument;
  onChange: (value: PromptDocument) => void;
  onSubmit: (value: PromptDocument) => void;
  medicineEntries: MedicineEntry[];
  isStreaming?: boolean;
  isStopping?: boolean;
  onAbort?: () => void;
  disabled?: boolean;
  canSend?: boolean;
}
export function MedicinePromptField({
  medicineEntries,
  ...props
}: MedicinePromptFieldProps) {
  const searchCompletions = useCallback(
    (query: string) =>
      searchMedicines(query, medicineEntries, 8).map((item, index) => ({
        id: `${item.y}-${item.n}-${index}`,
        label: item.n,
        token: {
          type: "custom" as const,
          anchor: "@",
          valueType: "medicine",
          data: {
            yj_code: item.y,
            name: item.n,
            standard: item.g ?? null,
            unit: item.c ?? null,
          },
        },
      })),
    [medicineEntries],
  );
  return (
    <TokenPromptInput
      {...props}
      searchCompletions={searchCompletions}
      serialize={buildPayloadContent}
      accessibleLabel="質問を入力"
      placeholder="質問を入力してください"
      testId="medicine-prompt-field"
      sendLabel="送信"
      stopLabel="回答を停止"
      stoppingLabel="停止中"
      lengthError={`質問は${props.maxLength}文字以内で入力してください。`}
    />
  );
}
