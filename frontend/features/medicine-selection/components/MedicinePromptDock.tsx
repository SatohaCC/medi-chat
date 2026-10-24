"use client";

import type { PromptFieldValue } from "@react-spectrum/ai";
import * as stylex from "@stylexjs/stylex";
import { Plus, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { MedicineEntry } from "../model/medicineAutocomplete";
import { MAX_TARGET_MEDICINES, type SelectedMedicineItem } from "../model/promptSnapshot";
import { styles } from "./MedicinePromptDock.styles";
import { MedicinePromptField } from "./MedicinePromptField";

export interface MedicinePromptDockProps {
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
  isStreaming?: boolean;
  isStopping?: boolean;
  onAbort?: () => void;
  disabled?: boolean;
  canSend?: boolean;
}

export function MedicinePromptDock({
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
  onAbort,
  disabled = false,
  canSend = true,
}: MedicinePromptDockProps) {
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const searchInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isAddOpen) {
      searchInputRef.current?.focus();
    }
  }, [isAddOpen]);

  const candidates = useMemo(() => {
    const currentYjs = new Set(baseline.map((m) => m.yj_code));
    const q = searchQuery.trim().toLowerCase();
    const available = medicineEntries.filter((m) => m.y && !currentYjs.has(m.y));
    if (!q) return available.slice(0, 15);
    return available
      .filter(
        (m) =>
          m.n.toLowerCase().includes(q) ||
          m.k?.toLowerCase().includes(q) ||
          m.h?.toLowerCase().includes(q) ||
          m.y.includes(q),
      )
      .slice(0, 20);
  }, [medicineEntries, baseline, searchQuery]);

  return (
    <div {...stylex.props(styles.container)} data-testid="medicine-prompt-dock">
      <div {...stylex.props(styles.inner)}>
        {/* Tier 1: 対象処方箋（ベース処方薬） */}
        <div {...stylex.props(styles.tier)} data-testid="tier-1-prescription">
          <span {...stylex.props(styles.tierLabel)}>対象処方箋:</span>
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
                  <X size={11} strokeWidth={2.5} />
                </button>
              </span>
            ))}
            {baseline.length === 0 && (
              <span {...stylex.props(styles.emptyNotice)}>なし</span>
            )}
          </div>

          {onAddBaseline && (
            <div {...stylex.props(styles.addBaselineWrapper)}>
              <button
                type="button"
                {...stylex.props(styles.addBaselineBtn)}
                onClick={() => {
                  setIsAddOpen((prev) => !prev);
                  setSearchQuery("");
                }}
                aria-expanded={isAddOpen}
                aria-label="処方薬を追加"
              >
                <Plus size={12} strokeWidth={2.5} />
                処方薬を追加
              </button>

              {isAddOpen && (
                <div
                  {...stylex.props(styles.popoverMenu)}
                  role="dialog"
                  aria-label="処方薬を選択"
                >
                  <div {...stylex.props(styles.popoverHeader)}>
                    <input
                      ref={searchInputRef}
                      type="search"
                      placeholder="薬名・YJコードで検索..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      {...stylex.props(styles.popoverSearchInput)}
                      aria-label="処方薬検索"
                    />
                    <button
                      type="button"
                      onClick={() => setIsAddOpen(false)}
                      {...stylex.props(styles.popoverCloseBtn)}
                      aria-label="検索を閉じる"
                    >
                      <X size={13} />
                    </button>
                  </div>
                  <div {...stylex.props(styles.popoverList)} role="listbox">
                    {candidates.length === 0 ? (
                      <div {...stylex.props(styles.popoverEmpty)}>
                        候補が見つかりません
                      </div>
                    ) : (
                      candidates.map((item, idx) => (
                        <button
                          key={`${item.y}-${item.n}-${idx}`}
                          type="button"
                          role="option"
                          {...stylex.props(styles.popoverItem)}
                          onClick={() => {
                            onAddBaseline({ yj_code: item.y, name: item.n });
                            setIsAddOpen(false);
                            setSearchQuery("");
                          }}
                        >
                          <span {...stylex.props(styles.popoverItemName)}>{item.n}</span>
                          {item.g && (
                            <span {...stylex.props(styles.popoverItemGeneric)}>
                              ({item.g})
                            </span>
                          )}
                        </button>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>
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

        {/* Tier 2: チャットでの追加薬 */}
        <div {...stylex.props(styles.tier)} data-testid="tier-2-additional">
          <span {...stylex.props(styles.tierLabel)}>チャットでの追加薬:</span>
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
                  <X size={11} strokeWidth={2.5} />
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
              全解除
            </button>
          )}
        </div>

        {/* Tier 3: PromptField */}
        <div {...stylex.props(styles.promptContainer)}>
          {baseline.length + additional.length > MAX_TARGET_MEDICINES && (
            <p role="alert">
              対象薬は最大{MAX_TARGET_MEDICINES}件です。選択を減らしてください。
            </p>
          )}
          <MedicinePromptField
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
