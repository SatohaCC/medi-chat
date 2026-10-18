"use client";

import type { PromptFieldValue } from "@react-spectrum/ai";
import * as stylex from "@stylexjs/stylex";
import type { MedicineEntry } from "../model/medicineAutocomplete";
import type { SelectedMedicineItem } from "../model/promptSnapshot";
import { styles } from "./MedicinePromptDock.styles";
import { MedicinePromptField } from "./MedicinePromptField";

export interface MedicinePromptDockProps {
  baseline: SelectedMedicineItem[];
  onRemoveBaseline: (yjCode: string) => void;
  onClearBaseline: () => void;
  additional: SelectedMedicineItem[];
  onRemoveAdditional: (yjCode: string) => void;
  onClearAdditional: () => void;
  prompt: PromptFieldValue;
  onChangePrompt: (prompt: PromptFieldValue) => void;
  onSubmit: (prompt: PromptFieldValue) => void;
  medicineEntries: MedicineEntry[];
  isStreaming?: boolean;
  disabled?: boolean;
  canSend?: boolean;
}

export function MedicinePromptDock({
  baseline,
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
  disabled = false,
  canSend = true,
}: MedicinePromptDockProps) {
  return (
    <div {...stylex.props(styles.container)} data-testid="medicine-prompt-dock">
      {/* Tier 1: 対象処方箋（ベース処方薬） */}
      <div {...stylex.props(styles.tier)} data-testid="tier-1-prescription">
        <span {...stylex.props(styles.tierLabel)}>📋 対象処方箋:</span>
        <div {...stylex.props(styles.chipList)}>
          {baseline.map((med) => (
            <span key={med.yj_code} {...stylex.props(styles.chip)}>
              <button
                type="button"
                {...stylex.props(styles.chipNameBtn)}
                aria-label={med.name}
              >
                {med.name}
              </button>
              <button
                type="button"
                aria-label={`処方箋から${med.name}を削除`}
                {...stylex.props(styles.chipRemoveBtn)}
                onClick={() => onRemoveBaseline(med.yj_code)}
              >
                ×
              </button>
            </span>
          ))}
          {baseline.length === 0 && (
            <span {...stylex.props(styles.emptyNotice)}>なし</span>
          )}
        </div>
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

      {/* Tier 2: チャットでの追加薬 */}
      <div {...stylex.props(styles.tier)} data-testid="tier-2-additional">
        <span {...stylex.props(styles.tierLabel)}>➕ チャットでの追加薬:</span>
        <div {...stylex.props(styles.chipList)}>
          {additional.map((med) => (
            <span key={med.yj_code} {...stylex.props(styles.additionalChip)}>
              <button
                type="button"
                {...stylex.props(styles.chipNameBtn)}
                aria-label={med.name}
              >
                {med.name}
              </button>
              <button
                type="button"
                aria-label={`追加薬から${med.name}を削除`}
                {...stylex.props(styles.chipRemoveBtn)}
                onClick={() => onRemoveAdditional(med.yj_code)}
              >
                ×
              </button>
            </span>
          ))}
          {additional.length === 0 && (
            <span {...stylex.props(styles.emptyNotice)}>なし</span>
          )}
        </div>
        {additional.length > 0 && (
          <button
            type="button"
            {...stylex.props(styles.actionBtn)}
            onClick={onClearAdditional}
          >
            今回はベースだけにする
          </button>
        )}
      </div>

      {/* Tier 3: PromptField */}
      <div {...stylex.props(styles.promptContainer)}>
        <MedicinePromptField
          value={prompt}
          onChange={onChangePrompt}
          onSubmit={onSubmit}
          medicineEntries={medicineEntries}
          isStreaming={isStreaming}
          disabled={disabled}
          canSend={canSend}
        />
      </div>
    </div>
  );
}
