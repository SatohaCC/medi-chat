"use client";

import type { PromptDocument } from "../../../../shared/component/TokenPromptInput/PromptDocument";
import type { MedicineEntry, SelectedMedicineItem } from "../../../medicine-selection";
import { MedicinePromptDock } from "../../../medicine-selection";
import type { ConnectionStatus } from "../../model/chat";
import { MAX_MESSAGE_LENGTH } from "../../model/chatLimits";

export interface ChatInputFormProps {
  baseline: SelectedMedicineItem[];
  onAddBaseline?: (medicine: SelectedMedicineItem) => void;
  onRemoveBaseline: (yjCode: string) => void;
  onClearBaseline: () => void;
  additional: SelectedMedicineItem[];
  onRemoveAdditional: (yjCode: string) => void;
  onClearAdditional: () => void;
  prompt: PromptDocument;
  onChangePrompt: (prompt: PromptDocument) => void;
  onSubmit: (prompt: PromptDocument) => void;
  medicineEntries: MedicineEntry[];
  status: ConnectionStatus;
  isStreaming: boolean;
  canSend: boolean;
  showSetupHint?: boolean;
  isStopping?: boolean;
  onAbort?: () => void;
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
  isStreaming,
  canSend,
  showSetupHint,
  isStopping = false,
  onAbort,
}: ChatInputFormProps) {
  return (
    <MedicinePromptDock
      maxLength={MAX_MESSAGE_LENGTH}
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
      disabled={false}
      isStreaming={isStreaming}
      isStopping={isStopping}
      showSetupHint={showSetupHint}
      onAbort={onAbort}
      canSend={canSend}
    />
  );
}
