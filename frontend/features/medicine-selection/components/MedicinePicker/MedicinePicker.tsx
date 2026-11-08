"use client";
import { useMemo, useState } from "react";
import { SearchablePicker } from "../../../../shared/component/SearchablePicker";
import type { MedicineEntry } from "../../model/medicineAutocomplete";
import type { SelectedMedicineItem } from "../../model/promptSnapshot";
export function MedicinePicker({
  entries,
  selected,
  onSelect,
  buttonLabel,
}: {
  entries: MedicineEntry[];
  selected: SelectedMedicineItem[];
  onSelect: (medicine: SelectedMedicineItem) => void;
  buttonLabel: string;
}) {
  const [query, setQuery] = useState("");
  const candidates = useMemo(() => {
    const selectedCodes = new Set(selected.map((medicine) => medicine.yj_code));
    const q = query.trim().toLowerCase();
    return entries
      .filter(
        (m) =>
          m.y &&
          !selectedCodes.has(m.y) &&
          (!q ||
            m.n.toLowerCase().includes(q) ||
            m.k?.toLowerCase().includes(q) ||
            m.h?.toLowerCase().includes(q) ||
            m.y.includes(q)),
      )
      .slice(0, q ? 20 : 15);
  }, [entries, selected, query]);
  return (
    <SearchablePicker
      items={candidates.map((m) => ({ id: m.y, label: m.n, description: m.g }))}
      query={query}
      onQueryChange={setQuery}
      onSelect={(id) => {
        const medicine = candidates.find((m) => m.y === id);
        if (medicine) onSelect({ yj_code: medicine.y, name: medicine.n });
      }}
      buttonLabel={buttonLabel}
      dialogLabel="処方薬を選択"
      searchLabel="薬名またはYJコード"
      searchAccessibleLabel="処方薬検索"
      placeholder="検索"
      closeLabel="検索を閉じる"
      closeText="閉じる"
      listLabel="処方薬の候補"
      emptyText="候補が見つかりません"
    />
  );
}
