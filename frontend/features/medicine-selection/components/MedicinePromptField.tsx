"use client";

import {
  InsertTokenMenuItem,
  PromptField,
  type PromptFieldValue,
  PromptTokenField,
} from "@react-spectrum/ai";
import { Button } from "@react-spectrum/s2/Button";
import Send from "@react-spectrum/s2/icons/ArrowUpSend";
import Stop from "@react-spectrum/s2/icons/StopProcessing";
import * as stylex from "@stylexjs/stylex";
import { useCallback, useEffect, useRef, useState } from "react";
import { TokenFieldContext } from "react-aria-components/TokenField";
import { MAX_MESSAGE_LENGTH } from "../../../shared/api/chatLimits";
import type { MedicineEntry } from "../model/medicineAutocomplete";
import { searchMedicines } from "../model/medicineAutocomplete";
import { buildPayloadContent } from "../model/promptSnapshot";
import { styles } from "./MedicinePromptField.styles";

export interface MedicinePromptFieldProps {
  value: PromptFieldValue;
  onChange: (value: PromptFieldValue) => void;
  onSubmit: (prompt: PromptFieldValue) => void;
  medicineEntries: MedicineEntry[];
  isStreaming?: boolean;
  isStopping?: boolean;
  onAbort?: () => void;
  disabled?: boolean;
  canSend?: boolean;
}

export function MedicinePromptField({
  value,
  onChange,
  onSubmit,
  medicineEntries,
  isStreaming = false,
  isStopping = false,
  onAbort,
  disabled = false,
  canSend = true,
}: MedicinePromptFieldProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [dismissedContent, setDismissedContent] = useState<string | null>(null);
  const content = buildPayloadContent(value).trim();
  const tooLong = Array.from(content).length > MAX_MESSAGE_LENGTH;
  const blocked = disabled || isStreaming || !canSend || !content || tooLong;

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
      if (dismissedContent === content) return null;
      const query = filterValue.replace(/^[@＠]/, "");
      if (!query.trim()) {
        return null;
      }
      const matches = searchMedicines(query, medicineEntries, 8);
      if (matches.length === 0) {
        return null;
      }
      return matches.map((item, idx) => (
        <InsertTokenMenuItem
          key={`${item.y}-${item.n}-${idx}`}
          id={`${item.y}-${item.n}-${idx}`}
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
    [medicineEntries, dismissedContent, content],
  );

  const handleSubmit = useCallback(
    (promptVal: PromptFieldValue) => {
      if (blocked) return;
      onSubmit(promptVal);
    },
    [blocked, onSubmit],
  );

  return (
    <div
      ref={containerRef}
      data-testid="medicine-prompt-field"
      onKeyDownCapture={(event) => {
        if (event.key === "Escape" && !event.nativeEvent.isComposing)
          setDismissedContent(content);
      }}
    >
      <PromptField
        value={value}
        onChange={(next) => {
          if (buildPayloadContent(next).trim() !== content) setDismissedContent(null);
          onChange(next);
        }}
        onSubmit={handleSubmit}
        isGenerating={isStreaming}
        aiDisclaimer=""
      >
        <TokenFieldContext.Provider value={{ isDisabled: disabled || isStreaming }}>
          <PromptTokenField
            completionTrigger={/[@＠]/}
            renderCompletions={renderCompletions}
            placeholder="確認したい内容を入力 (例: この処方に @ロキソニン を追加してもよい？)..."
          />
        </TokenFieldContext.Provider>
        <div {...stylex.props(styles.submit)}>
          <Button
            variant="primary"
            staticColor="auto"
            aria-label={isStreaming ? (isStopping ? "停止中" : "回答を停止") : "送信"}
            isDisabled={isStreaming ? isStopping : Boolean(blocked)}
            onPress={() => {
              if (isStreaming) {
                if (!isStopping) onAbort?.();
              } else handleSubmit(value);
            }}
          >
            {isStreaming ? <Stop /> : <Send />}
          </Button>
          {isStopping && <span role="status">停止中</span>}
        </div>
      </PromptField>
      {tooLong && (
        <p role="alert">質問は{MAX_MESSAGE_LENGTH}文字以内で入力してください。</p>
      )}
    </div>
  );
}
