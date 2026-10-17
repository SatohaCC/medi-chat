import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
  const { items: activeItems } = useActiveMedicines();
  const [dictionaryEntries, setDictionaryEntries] = useState<MedicineEntry[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [suggestions, setSuggestions] = useState<MedicineEntry[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [activeToken, setActiveToken] = useState("");
  const [tokenRange, setTokenRange] = useState<[number, number]>([0, 0]);

  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const justAcceptedRef = useRef(false);

  // Load full medicines dictionary from /data/medicines.json on mount
  useEffect(() => {
    let cancelled = false;
    async function loadDictionary() {
      try {
        const res = await fetch("/data/medicines.json");
        if (!res.ok) return;
        const data = (await res.json()) as MedicineEntry[];
        if (!cancelled && Array.isArray(data)) {
          setDictionaryEntries(data);
        }
      } catch {
        // Ignore dictionary fetch errors and fall back to activeItems
      }
    }
    void loadDictionary();
    return () => {
      cancelled = true;
    };
  }, []);

  const entries = useMemo(() => {
    if (dictionaryEntries.length === 0) return activeItems;
    if (activeItems.length === 0) return dictionaryEntries;

    const dictByYj = new Map<string, MedicineEntry>();
    for (const item of dictionaryEntries) {
      if (item.y && !dictByYj.has(item.y)) {
        dictByYj.set(item.y, item);
      }
    }

    const activeYjs = new Set<string>();
    const merged: MedicineEntry[] = [];

    for (const active of activeItems) {
      activeYjs.add(active.y);
      const dict = dictByYj.get(active.y);
      if (dict) {
        merged.push({
          n: active.n || dict.n,
          k: active.k || dict.k,
          h: active.h || dict.h,
          y: active.y,
          g: active.g || dict.g,
          c: active.c && active.c !== "他" ? active.c : dict.c || active.c,
        });
      } else {
        merged.push(active);
      }
    }

    for (const item of dictionaryEntries) {
      if (!activeYjs.has(item.y)) {
        merged.push(item);
      }
    }

    return merged;
  }, [activeItems, dictionaryEntries]);

  // Update suggestions based on text at cursor
  const updateSuggestions = useCallback(
    (currentVal: string, cursor: number) => {
      if (entries.length === 0) {
        setIsOpen(false);
        return;
      }

      const textBefore = currentVal.slice(0, cursor);
      const match = textBefore.match(
        /([a-zA-Z0-9.\uFF10-\uFF19\uFF21-\uFF3A\uFF41-\uFF5A\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAFー「」]+)$/,
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
    if (justAcceptedRef.current) {
      justAcceptedRef.current = false;
      return;
    }
    updateSuggestions(value, inputRef.current?.selectionStart ?? value.length);
  }, [updateSuggestions, value]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    justAcceptedRef.current = false;
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
    (entry: MedicineEntry, keepOpenOnRevalidate = false) => {
      const [start, end] = tokenRange;
      const before = value.slice(0, start);
      const after = value.slice(end);
      const completedText = before + entry.n + after;

      justAcceptedRef.current = !keepOpenOnRevalidate;
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
      acceptSuggestion(suggestions[selectedIndex], e.nativeEvent.isComposing);
      return;
    }

    if (e.key === "Enter") {
      e.preventDefault();
      acceptSuggestion(suggestions[selectedIndex], e.nativeEvent.isComposing);
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
