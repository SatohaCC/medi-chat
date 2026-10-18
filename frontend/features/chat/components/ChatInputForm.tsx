"use client";

import type { PromptFieldValue } from "@react-spectrum/ai";
import type { MedicineEntry, SelectedMedicineItem } from "../../medicine-selection";
import { MedicinePromptDock } from "../../medicine-selection";
import type { ConnectionStatus } from "../model/chat";

export interface ChatInputFormProps {
  baseline: SelectedMedicineItem[];
  onAddBaseline?: (medicine: SelectedMedicineItem) => void;
  onRemoveBaseline: (yjCode: string) => void;
  onClearBaseline: () => void;
  additional: SelectedMedicineItem[];
  onRemoveAdditional: (yjCode: string) => void;
  onClearAdditional: () => void;
  prompt: PromptFieldValue;
  onChangePrompt: (prompt: PromptFieldValue) => void;
  onSubmit: (prompt: PromptFieldValue) => void;
  medicineEntries: MedicineEntry[];
  status: ConnectionStatus;
  isStreaming: boolean;
  canSend: boolean;
}

export function ChatInputForm({
  baseline,
  onAddBaseline,
  onRemoveBaseline,
  onClearBaseline,
  additional,
  onRemoveAdditional,
  onClearAdditional,
  prompt,
  onChangePrompt,
  onSubmit,
  medicineEntries,
  status,
  isStreaming,
  canSend,
}: ChatInputFormProps) {
  return (
    <MedicinePromptDock
      baseline={baseline}
      onAddBaseline={onAddBaseline}
      onRemoveBaseline={onRemoveBaseline}
      onClearBaseline={onClearBaseline}
      additional={additional}
      onRemoveAdditional={onRemoveAdditional}
      onClearAdditional={onClearAdditional}
      prompt={prompt}
      onChangePrompt={onChangePrompt}
      onSubmit={onSubmit}
      medicineEntries={medicineEntries}
      disabled={status !== "connected"}
      isStreaming={isStreaming}
      canSend={canSend}
    />
  );
}
