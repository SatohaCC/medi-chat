import { useCallback, useEffect, useRef, useState } from "react";
import { type MedicineEntry, searchMedicines } from "../model/medicineAutocomplete";
import { useActiveMedicines } from "./useActiveMedicines";

interface UseMedicineAutocompleteOptions {
  value: string;
  onChange: (value: string) => void;
  onSubmit?: () => void;
  onSelectMedicine?: (medicine: MedicineEntry) => void;
}

export function useMedicineAutocomplete({
  value,
  onChange,
  onSubmit,
  onSelectMedicine,
}: UseMedicineAutocompleteOptions) {
  const { items: entries } = useActiveMedicines();
  const [isOpen, setIsOpen] = useState(false);
  const [suggestions, setSuggestions] = useState<MedicineEntry[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [activeToken, setActiveToken] = useState("");
  const [tokenRange, setTokenRange] = useState<[number, number]>([0, 0]);

  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Update suggestions based on text at cursor
  const updateSuggestions = useCallback(
    (currentVal: string, cursor: number) => {
      if (entries.length === 0) {
        setIsOpen(false);
        return;
      }

      const textBefore = currentVal.slice(0, cursor);
      const match = textBefore.match(
        /([a-zA-Z0-9\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAFー]+)$/,
      );

      if (!match) {
        setIsOpen(false);
        return;
      }

      const token = match[1];
      const start = cursor - token.length;

      const hasKanji = /[\u4E00-\u9FAF]/.test(token);
      if (token.length < 2 && !hasKanji) {
        setIsOpen(false);
        return;
      }

      const results = searchMedicines(token, entries, 8);
      if (results.length > 0) {
        setSuggestions(results);
        setActiveToken(token);
        setTokenRange([start, cursor]);
        setSelectedIndex(0);
        setIsOpen(true);
      } else {
        setIsOpen(false);
      }
    },
    [entries],
  );

  useEffect(() => {
    updateSuggestions(value, inputRef.current?.selectionStart ?? value.length);
  }, [updateSuggestions, value]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVal = e.target.value;
    onChange(newVal);
    const cursor = e.target.selectionStart ?? newVal.length;
    updateSuggestions(newVal, cursor);
  };

  const handleKeyUp = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) {
      const cursor = inputRef.current?.selectionStart ?? value.length;
      updateSuggestions(value, cursor);
    }
  };

  const acceptSuggestion = useCallback(
    (entry: MedicineEntry) => {
      const [start, end] = tokenRange;
      const before = value.slice(0, start);
      const after = value.slice(end);
      const completedText = before + entry.n + after;

      onChange(completedText);
      setIsOpen(false);

      if (onSelectMedicine) {
        onSelectMedicine(entry);
      }

      requestAnimationFrame(() => {
        if (inputRef.current) {
          inputRef.current.focus();
          const newCursor = start + entry.n.length;
          inputRef.current.setSelectionRange(newCursor, newCursor);
        }
      });
    },
    [value, tokenRange, onChange, onSelectMedicine],
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!isOpen || suggestions.length === 0) {
      if (e.key === "Enter" && onSubmit) {
        return;
      }
      return;
    }

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % suggestions.length);
      return;
    }

    if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + suggestions.length) % suggestions.length);
      return;
    }

    if (e.key === "Tab") {
      e.preventDefault();
      acceptSuggestion(suggestions[selectedIndex]);
      return;
    }

    if (e.key === "Enter") {
      e.preventDefault();
      acceptSuggestion(suggestions[selectedIndex]);
      return;
    }

    if (e.key === "Escape") {
      e.preventDefault();
      setIsOpen(false);
      return;
    }
  };

  useEffect(() => {
    if (isOpen && listRef.current) {
      const activeEl = listRef.current.children[selectedIndex] as HTMLElement;
      if (activeEl) {
        activeEl.scrollIntoView({ block: "nearest" });
      }
    }
  }, [isOpen, selectedIndex]);

  return {
    isOpen,
    setIsOpen,
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
  };
}
