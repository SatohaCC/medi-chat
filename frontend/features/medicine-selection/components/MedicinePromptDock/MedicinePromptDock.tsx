"use client";

import * as stylex from "@stylexjs/stylex";
import { RemovableTags } from "../../../../shared/component/RemovableTags";
import type { PromptDocument } from "../../../../shared/component/TokenPromptInput/PromptDocument";
import type { MedicineEntry } from "../../model/medicineAutocomplete";
import {
  MAX_TARGET_MEDICINES,
  type SelectedMedicineItem,
} from "../../model/promptSnapshot";
import { MedicinePicker } from "../MedicinePicker";
import { MedicinePromptField } from "../MedicinePromptField";
import { styles } from "./MedicinePromptDock.styles";

export interface MedicinePromptDockProps {
  maxLength: number;
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
  isStreaming?: boolean;
  isStopping?: boolean;
  showSetupHint?: boolean;
  onAbort?: () => void;
  disabled?: boolean;
  canSend?: boolean;
}

export function MedicinePromptDock({
  maxLength,
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
  isStreaming = false,
  isStopping = false,
  showSetupHint = true,
  onAbort,
  disabled = false,
  canSend = true,
}: MedicinePromptDockProps) {
  return (
    <div {...stylex.props(styles.container)} data-testid="medicine-prompt-dock">
      <div {...stylex.props(styles.inner)}>
        {showSetupHint && (
          <p>
            薬名を書くだけでは検索対象は変わりません。対象薬は上から、質問に追加する薬は「@」から選べます。
          </p>
        )}

        {/* 送信する質問の検索対象 */}
        <div {...stylex.props(styles.tier)} data-testid="tier-1-prescription">
          <span {...stylex.props(styles.tierLabel)}>対象薬:</span>
          <div {...stylex.props(styles.chipList)}>
            {baseline.length > 0 ? (
              <RemovableTags
                label="この質問で調べる薬"
                items={baseline.map((med) => ({ id: med.yj_code, label: med.name }))}
                onRemove={onRemoveBaseline}
                tone="accent"
                removeLabel={(name) => `削除 ${name}`}
              />
            ) : (
              <span {...stylex.props(styles.emptyNotice)}>未選択</span>
            )}
          </div>
          {onAddBaseline && (
            <MedicinePicker
              entries={medicineEntries}
              selected={baseline}
              onSelect={onAddBaseline}
              buttonLabel={baseline.length === 0 ? "調べる薬を選ぶ" : "薬を追加"}
            />
          )}

          {baseline.length > 0 && (
            <button
              type="button"
              {...stylex.props(styles.actionBtn)}
              onClick={onClearBaseline}
            >
              全解除
            </button>
          )}
        </div>

        {/* 質問文の @ から追加した薬 */}
        {additional.length > 0 && (
          <div {...stylex.props(styles.tier)} data-testid="tier-2-additional">
            <span {...stylex.props(styles.tierLabel)}>質問文から追加した薬:</span>
            <div {...stylex.props(styles.chipList)}>
              <RemovableTags
                label="質問文から追加した薬"
                items={additional.map((med) => ({ id: med.yj_code, label: med.name }))}
                onRemove={onRemoveAdditional}
                tone="positive"
                removeLabel={(name) => `削除 ${name}`}
              />
            </div>
            <button
              type="button"
              {...stylex.props(styles.actionBtn)}
              onClick={onClearAdditional}
            >
              全解除
            </button>
          </div>
        )}

        {/* Tier 3: PromptField */}
        <div {...stylex.props(styles.promptContainer)}>
          {baseline.length + additional.length > MAX_TARGET_MEDICINES && (
            <p role="alert">
              対象薬は最大{MAX_TARGET_MEDICINES}件です。選択を減らしてください。
            </p>
          )}
          <MedicinePromptField
            maxLength={maxLength}
            value={prompt}
            onChange={onChangePrompt}
            onSubmit={onSubmit}
            medicineEntries={medicineEntries}
            isStreaming={isStreaming}
            isStopping={isStopping}
            onAbort={onAbort}
            disabled={disabled}
            canSend={canSend}
          />
        </div>
      </div>
    </div>
  );
}
