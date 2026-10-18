import { useEffect, useMemo, useState } from "react";
import type { MedicineEntry } from "../model/medicineAutocomplete";
import { mergeMedicineEntries } from "../model/medicineEntries";
import { useActiveMedicines } from "./useActiveMedicines";

let cachedStaticEntries: MedicineEntry[] | null = null;
let staticEntriesPromise: Promise<MedicineEntry[]> | null = null;

export async function fetchStaticMedicines(): Promise<MedicineEntry[]> {
  if (cachedStaticEntries) return cachedStaticEntries;
  if (!staticEntriesPromise) {
    staticEntriesPromise = fetch("/data/medicines.json")
      .then((res) => (res.ok ? res.json() : []))
      .then((data: unknown) => {
        const valid = Array.isArray(data)
          ? (data as MedicineEntry[]).filter(
              (item) => typeof item.y === "string" && item.y.trim().length > 0,
            )
          : [];
        cachedStaticEntries = valid;
        return valid;
      })
      .catch(() => []);
  }
  return staticEntriesPromise;
}

export { mergeMedicineEntries };

export function useMedicineEntries() {
  const activeMedicines = useActiveMedicines();
  const [staticEntries, setStaticEntries] = useState<MedicineEntry[]>(
    () => cachedStaticEntries || [],
  );

  useEffect(() => {
    if (!cachedStaticEntries) {
      let cancelled = false;
      void fetchStaticMedicines().then((items) => {
        if (!cancelled) setStaticEntries(items);
      });
      return () => {
        cancelled = true;
      };
    }
  }, []);

  const entries = useMemo(() => {
    return mergeMedicineEntries(activeMedicines.items, staticEntries);
  }, [activeMedicines.items, staticEntries]);

  return {
    entries,
    activeMedicines,
  };
}
