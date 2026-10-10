"use client";

import { useMedicineAutocomplete } from "../hooks/useMedicineAutocomplete";
import type { MedicineEntry } from "../lib/medicineAutocomplete";

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
    <div style={{ position: "relative", flex: 1, display: "flex" }}>
      <input
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
        style={{
          width: "100%",
          padding: "10px 14px",
          background: "var(--assistant-bg)",
          color: "var(--fg)",
          border: "1px solid var(--border)",
          borderRadius: "8px",
          fontSize: "15px",
          outline: "none",
        }}
      />

      {isOpen && suggestions.length > 0 && (
        <div
          style={{
            position: "absolute",
            bottom: "calc(100% + 8px)",
            left: 0,
            right: 0,
            background: "#18181b",
            border: "1px solid #3b82f6",
            borderRadius: "8px",
            boxShadow:
              "0 12px 28px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(59, 130, 246, 0.2)",
            overflow: "hidden",
            zIndex: 100,
            display: "flex",
            flexDirection: "column",
            maxHeight: "360px",
          }}
        >
          {/* Header bar */}
          <div
            style={{
              padding: "6px 12px",
              background: "#111827",
              borderBottom: "1px solid #374151",
              fontSize: "11px",
              color: "#9ca3af",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <span>
              💊 医薬品サジェスト (キー:{" "}
              <strong style={{ color: "#60a5fa" }}>{activeToken}</strong>)
            </span>
            <span style={{ fontSize: "10px", color: "#6b7280" }}>
              {suggestions.length} 件
            </span>
          </div>

          {/* Suggestions List */}
          <div
            ref={listRef}
            role="listbox"
            aria-label="医薬品サジェスト候補"
            style={{
              overflowY: "auto",
              display: "flex",
              flexDirection: "column",
            }}
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
                  style={{
                    padding: "8px 12px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "3px",
                    cursor: "pointer",
                    background: isSelected ? "#1e3a8a" : "transparent",
                    borderLeft: isSelected
                      ? "3px solid #60a5fa"
                      : "3px solid transparent",
                    transition: "background 0.1s ease",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: "8px",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                      }}
                    >
                      <span
                        style={{
                          fontSize: "10px",
                          padding: "1px 5px",
                          borderRadius: "4px",
                          background:
                            item.c === "内用"
                              ? "#1e40af"
                              : item.c === "外用"
                                ? "#92400e"
                                : item.c === "注射"
                                  ? "#065f46"
                                  : "#4b5563",
                          color: "#f3f4f6",
                          fontWeight: 500,
                        }}
                      >
                        {item.c || "医薬"}
                      </span>
                      <span
                        style={{
                          fontSize: "14px",
                          fontWeight: 600,
                          color: isSelected ? "#ffffff" : "#f3f4f6",
                        }}
                      >
                        {item.n}
                      </span>
                    </div>
                    <span
                      style={{
                        fontSize: "11px",
                        fontFamily: "monospace",
                        color: isSelected ? "#93c5fd" : "#6b7280",
                      }}
                    >
                      {item.y}
                    </span>
                  </div>

                  <div
                    style={{
                      display: "flex",
                      gap: "10px",
                      fontSize: "11px",
                      color: isSelected ? "#bfdbfe" : "#9ca3af",
                      paddingLeft: "4px",
                    }}
                  >
                    <span>読み: {item.k || item.h}</span>
                    {item.g && <span>一般名: {item.g}</span>}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Footer Guide */}
          <div
            style={{
              padding: "4px 12px",
              background: "#111827",
              borderTop: "1px solid #1f2937",
              fontSize: "11px",
              color: "#6b7280",
              display: "flex",
              gap: "12px",
            }}
          >
            <span>
              <kbd
                style={{
                  background: "#374151",
                  color: "#e5e7eb",
                  padding: "1px 4px",
                  borderRadius: "3px",
                  fontSize: "10px",
                }}
              >
                Tab
              </kbd>{" "}
              確定
            </span>
            <span>
              <kbd
                style={{
                  background: "#374151",
                  color: "#e5e7eb",
                  padding: "1px 4px",
                  borderRadius: "3px",
                  fontSize: "10px",
                }}
              >
                ↑↓
              </kbd>{" "}
              選択
            </span>
            <span>
              <kbd
                style={{
                  background: "#374151",
                  color: "#e5e7eb",
                  padding: "1px 4px",
                  borderRadius: "3px",
                  fontSize: "10px",
                }}
              >
                Esc
              </kbd>{" "}
              閉じる
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
