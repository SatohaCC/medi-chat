import { useCallback, useEffect, useState } from "react";
import { backendBaseUrl } from "../lib/api";
import type {
  CustomMedicine,
  MedicineCatalogStatus,
  MedicineOption,
} from "../types/chat";

export function useMedicineCatalog(defaultYjCode = "3339003F5020") {
  const [selectedYjCodes, setSelectedYjCodes] = useState<string[]>([defaultYjCode]);
  const [medicineOptions, setMedicineOptions] = useState<MedicineOption[]>([]);
  const [medicineCatalogStatus, setMedicineCatalogStatus] =
    useState<MedicineCatalogStatus>("loading");
  const [customMedicines, setCustomMedicines] = useState<CustomMedicine[]>([]);

  useEffect(() => {
    const controller = new AbortController();

    async function loadMedicineCatalog() {
      try {
        const response = await fetch(`${backendBaseUrl()}/api/medicines`, {
          signal: controller.signal,
        });
        if (!response.ok) {
          throw new Error(`Medicine catalog failed: ${response.status}`);
        }
        const data = (await response.json()) as { items: MedicineOption[] };
        if (controller.signal.aborted) return;

        setMedicineOptions(data.items);
        setMedicineCatalogStatus("ready");

        const availableCodes = new Set(
          data.items.flatMap((medicine) => medicine.yj_codes),
        );
        setSelectedYjCodes((previous) => {
          const retained = previous.filter((code) => availableCodes.has(code));
          if (retained.length > 0) return retained;
          const firstCode = data.items.flatMap((medicine) => medicine.yj_codes)[0];
          return firstCode ? [firstCode] : previous;
        });
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return;
        if (!controller.signal.aborted) {
          setMedicineCatalogStatus("error");
        }
      }
    }

    loadMedicineCatalog();
    return () => controller.abort();
  }, []);

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
    setSelectedYjCodes,
    medicineOptions,
    medicineCatalogStatus,
    customMedicines,
    toggleYjCode,
    handleSelectMedicineFromAutocomplete,
  };
}
