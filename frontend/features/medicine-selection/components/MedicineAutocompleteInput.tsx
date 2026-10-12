"use client";

import * as stylex from "@stylexjs/stylex";
import { useMedicineAutocomplete } from "../hooks/useMedicineAutocomplete";
import type { MedicineEntry } from "../model/medicineAutocomplete";
import { styles } from "./MedicineAutocompleteInput.styles";

interface MedicineAutocompleteInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit?: () => void;
  onSelectMedicine?: (medicine: MedicineEntry) => void;
  placeholder?: string;
  disabled?: boolean;
}

export function MedicineAutocompleteInput({
  value,
  onChange,
  onSubmit,
  onSelectMedicine,
  placeholder = "Type a message...",
  disabled = false,
}: MedicineAutocompleteInputProps) {
  const {
    isOpen,
    suggestions,
    selectedIndex,
    setSelectedIndex,
    activeToken,
    inputRef,
    listRef,
    handleInputChange,
    handleKeyUp,
    handleKeyDown,
    acceptSuggestion,
  } = useMedicineAutocomplete({
    value,
    onChange,
    onSubmit,
    onSelectMedicine,
  });

  return (
    <div {...stylex.props(styles.root)}>
      <input
        {...stylex.props(styles.input, styles.inputPresentation)}
        ref={inputRef}
        type="text"
        role="combobox"
        value={value}
        onChange={handleInputChange}
        onKeyUp={handleKeyUp}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        aria-autocomplete="list"
        aria-expanded={isOpen}
      />

      {isOpen && suggestions.length > 0 && (
        <div {...stylex.props(styles.popup)}>
          {/* Header bar */}
          <div {...stylex.props(styles.popupHeader)}>
            <span>
              💊 医薬品サジェスト (キー:{" "}
              <strong {...stylex.props(styles.activeToken)}>{activeToken}</strong>)
            </span>
            <span {...stylex.props(styles.candidateCount)}>{suggestions.length} 件</span>
          </div>

          {/* Suggestions List */}
          <div
            ref={listRef}
            role="listbox"
            aria-label="医薬品サジェスト候補"
            {...stylex.props(styles.candidateList)}
          >
            {suggestions.map((item, idx) => {
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={`${item.y}-${item.n}`}
                  role="option"
                  aria-selected={isSelected}
                  tabIndex={-1}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    acceptSuggestion(item);
                  }}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  {...stylex.props(
                    styles.suggestion(
                      isSelected ? "#1e3a8a" : "transparent",
                      isSelected ? "#60a5fa" : "transparent",
                    ),
                  )}
                >
                  <div {...stylex.props(styles.suggestionHeading)}>
                    <div {...stylex.props(styles.productNameRow)}>
                      <span
                        {...stylex.props(
                          styles.category(
                            item.c === "内用"
                              ? "#1e40af"
                              : item.c === "外用"
                                ? "#92400e"
                                : item.c === "注射"
                                  ? "#065f46"
                                  : "#4b5563",
                          ),
                        )}
                      >
                        {item.c || "医薬"}
                      </span>
                      <span
                        {...stylex.props(
                          styles.productName(isSelected ? "#ffffff" : "#f3f4f6"),
                        )}
                      >
                        {item.n}
                      </span>
                    </div>
                    <span
                      {...stylex.props(styles.yjCode(isSelected ? "#93c5fd" : "#6b7280"))}
                    >
                      {item.y}
                    </span>
                  </div>

                  <div
                    {...stylex.props(
                      styles.productReading(isSelected ? "#bfdbfe" : "#9ca3af"),
                    )}
                  >
                    <span>読み: {item.k || item.h}</span>
                    {item.g && <span>一般名: {item.g}</span>}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Footer Guide */}
          <div {...stylex.props(styles.popupFooter)}>
            <span>
              <kbd {...stylex.props(styles.tabKey)}>Tab</kbd> 確定
            </span>
            <span>
              <kbd {...stylex.props(styles.arrowKey)}>↑↓</kbd> 選択
            </span>
            <span>
              <kbd {...stylex.props(styles.escapeKey)}>Esc</kbd> 閉じる
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
