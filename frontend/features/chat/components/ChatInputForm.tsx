import * as stylex from "@stylexjs/stylex";
import type React from "react";
import { Button } from "../../../shared/ui/Button";
import type { MedicineEntry } from "../../medicine-selection";
import { MedicineAutocompleteInput } from "../../medicine-selection";
import type { ConnectionStatus } from "../model/chat";
import { styles } from "./ChatInputForm.styles";

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
    <form {...stylex.props(styles.form)} onSubmit={onSubmit}>
      <div {...stylex.props(styles.inputSlot)}>
        <MedicineAutocompleteInput
          value={input}
          onChange={onChangeInput}
          onSubmit={onSubmit}
          onSelectMedicine={onSelectMedicine}
          placeholder="確認したい内容を入力 (例: 禁忌、飲み合わせ、用法・用量)..."
          disabled={status !== "connected" || isStreaming}
        />
      </div>
      <Button type="submit" disabled={isSendDisabled}>
        Send
      </Button>
    </form>
  );
}
