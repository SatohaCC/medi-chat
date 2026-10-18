import type { MedicineEntry } from "./medicineAutocomplete";

export function mergeMedicineEntries(
  activeItems: MedicineEntry[],
  dictionaryEntries: MedicineEntry[],
): MedicineEntry[] {
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
    if (item.y && !activeYjs.has(item.y)) {
      merged.push(item);
    }
  }

  return merged;
}
