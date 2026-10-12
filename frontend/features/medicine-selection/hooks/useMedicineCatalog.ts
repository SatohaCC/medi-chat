import { useCallback, useState } from "react";
import type { CustomMedicine } from "../model/medicine";
import { useActiveMedicines } from "./useActiveMedicines";

export function useMedicineCatalog(defaultYjCode = "3339003F5020") {
  const [selectedYjCodes, setSelectedYjCodes] = useState<string[]>([defaultYjCode]);
  const active = useActiveMedicines();
  const medicineOptions = active.groups;
  const medicineCatalogStatus = active.status;
  const [customMedicines, setCustomMedicines] = useState<CustomMedicine[]>([]);
  const availableCodes = new Set(active.items.map((entry) => entry.y));
  const missingSelectedYjCodes =
    active.status === "ready"
      ? selectedYjCodes.filter((code) => !availableCodes.has(code))
      : [];

  const toggleYjCode = useCallback((code: string) => {
    setSelectedYjCodes((prev) =>
      prev.includes(code)
        ? prev.length > 1
          ? prev.filter((c) => c !== code)
          : prev
        : [...prev, code],
    );
  }, []);

  const handleSelectMedicineFromAutocomplete = useCallback(
    (medicine: { n: string; y: string }, currentInput: string) => {
      if (!medicine.y) return;
      setSelectedYjCodes((prev) => {
        // If only default placeholder is present and user didn't mention it, switch to the selected drug
        if (
          prev.length === 1 &&
          prev[0] === defaultYjCode &&
          !currentInput.includes("イグザレルト")
        ) {
          return [medicine.y];
        }
        return prev.includes(medicine.y) ? prev : [...prev, medicine.y];
      });
      setCustomMedicines((prev) => {
        if (prev.some((m) => m.yj_code === medicine.y)) return prev;
        return [...prev, { name: medicine.n, yj_code: medicine.y }];
      });
    },
    [defaultYjCode],
  );

  return {
    selectedYjCodes,
    missingSelectedYjCodes,
    setSelectedYjCodes,
    medicineOptions,
    medicineCatalogStatus,
    customMedicines,
    toggleYjCode,
    handleSelectMedicineFromAutocomplete,
  };
}
