"use client";

import {
  InsertTokenMenuItem,
  PromptField,
  PromptFieldSubmitButton,
  type PromptFieldValue,
  PromptTokenField,
} from "@react-spectrum/ai";
import { useCallback, useEffect, useRef } from "react";
import type { MedicineEntry } from "../model/medicineAutocomplete";
import { searchMedicines } from "../model/medicineAutocomplete";

export interface MedicinePromptFieldProps {
  value: PromptFieldValue;
  onChange: (value: PromptFieldValue) => void;
  onSubmit: (prompt: PromptFieldValue) => void;
  medicineEntries: MedicineEntry[];
  isStreaming?: boolean;
  disabled?: boolean;
  canSend?: boolean;
}

export function MedicinePromptField({
  value,
  onChange,
  onSubmit,
  medicineEntries,
  isStreaming = false,
  disabled = false,
  canSend = true,
}: MedicinePromptFieldProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (containerRef.current) {
      const textbox = containerRef.current.querySelector('[role="textbox"]');
      if (textbox) {
        textbox.setAttribute("aria-label", "質問を入力");
      }
    }
  }, []);

  const renderCompletions = useCallback(
    (filterValue: string) => {
      const query = filterValue.replace(/^[@＠]/, "");
      if (!query.trim()) {
        return null;
      }
      const matches = searchMedicines(query, medicineEntries, 8);
      if (matches.length === 0) {
        return null;
      }
      return matches.map((item) => (
        <InsertTokenMenuItem
          key={item.y}
          id={item.y}
          textValue={item.n}
          token={{
            type: "token",
            text: item.n,
            value: {
              type: "custom",
              anchor: "@",
              valueType: "medicine",
              data: {
                yj_code: item.y,
                name: item.n,
                standard: item.g ?? null,
                unit: item.c ?? null,
              },
            },
          }}
        >
          {item.n}
        </InsertTokenMenuItem>
      ));
    },
    [medicineEntries],
  );

  const handleSubmit = useCallback(
    (promptVal: PromptFieldValue) => {
      if (disabled || isStreaming || !canSend) return;
      onSubmit(promptVal);
    },
    [disabled, isStreaming, canSend, onSubmit],
  );

  return (
    <div ref={containerRef} data-testid="medicine-prompt-field">
      <PromptField
        value={value}
        onChange={onChange}
        onSubmit={handleSubmit}
        isGenerating={isStreaming}
        aiDisclaimer=""
      >
        <PromptTokenField
          completionTrigger={/[@＠]/}
          renderCompletions={renderCompletions}
          placeholder="確認したい内容を入力 (例: この処方に @ロキソニン を追加してもよい？)..."
        />
        <PromptFieldSubmitButton aria-label="送信" />
      </PromptField>
    </div>
  );
}
