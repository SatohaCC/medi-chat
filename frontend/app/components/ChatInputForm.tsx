import type React from "react";
import type { MedicineEntry } from "../lib/medicineAutocomplete";
import type { ConnectionStatus } from "../types/chat";
import { MedicineAutocompleteInput } from "./MedicineAutocompleteInput";

interface ChatInputFormProps {
  input: string;
  onChangeInput: (value: string) => void;
  onSubmit: (e?: React.FormEvent) => void;
  onSelectMedicine: (medicine: MedicineEntry) => void;
  selectedYjCodes: string[];
  status: ConnectionStatus;
  isStreaming: boolean;
}

export function ChatInputForm({
  input,
  onChangeInput,
  onSubmit,
  onSelectMedicine,
  selectedYjCodes,
  status,
  isStreaming,
}: ChatInputFormProps) {
  const isSendDisabled =
    !input.trim() ||
    selectedYjCodes.length === 0 ||
    status !== "connected" ||
    isStreaming;

  return (
    <form onSubmit={onSubmit}>
      <div style={{ flex: 1, minWidth: 0, display: "flex" }}>
        <MedicineAutocompleteInput
          value={input}
          onChange={onChangeInput}
          onSubmit={onSubmit}
          onSelectMedicine={onSelectMedicine}
          placeholder="確認したい内容を入力 (例: 禁忌、飲み合わせ、用法・用量)..."
          disabled={status !== "connected" || isStreaming}
        />
      </div>
      <button type="submit" disabled={isSendDisabled}>
        Send
      </button>
    </form>
  );
}
