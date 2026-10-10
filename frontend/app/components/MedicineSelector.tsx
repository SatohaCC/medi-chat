import type {
  CustomMedicine,
  MedicineCatalogStatus,
  MedicineOption,
} from "../types/chat";

interface MedicineSelectorProps {
  medicineOptions: MedicineOption[];
  medicineCatalogStatus: MedicineCatalogStatus;
  selectedYjCodes: string[];
  customMedicines: CustomMedicine[];
  onToggleYjCode: (code: string) => void;
}

export function MedicineSelector({
  medicineOptions,
  medicineCatalogStatus,
  selectedYjCodes,
  customMedicines,
  onToggleYjCode,
}: MedicineSelectorProps) {
  return (
    <div
      style={{
        padding: "10px 20px",
        borderBottom: "1px solid var(--border)",
        background: "var(--assistant-bg)",
        display: "flex",
        flexDirection: "column",
        gap: "8px",
      }}
    >
      <div style={{ fontSize: "12px", color: "var(--muted)", fontWeight: 500 }}>
        対象医薬品（YJコードで特定・複数選択可）:
      </div>
      {medicineCatalogStatus === "loading" && (
        <div style={{ fontSize: "12px", color: "var(--muted)" }}>
          対応医薬品を読み込み中…
        </div>
      )}
      {medicineCatalogStatus === "error" && (
        <div style={{ fontSize: "12px", color: "#fca5a5" }}>
          対応医薬品を取得できませんでした。バックエンドとの接続を確認してください。
        </div>
      )}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
        {medicineOptions.flatMap((medicine) =>
          medicine.yj_codes.map((yjCode, index) => {
            const isSelected = selectedYjCodes.includes(yjCode);
            const productName =
              medicine.brand_names[index] ??
              medicine.brand_names[0] ??
              medicine.generic_name;
            return (
              <button
                key={yjCode}
                type="button"
                onClick={() => onToggleYjCode(yjCode)}
                aria-pressed={isSelected}
                style={{
                  padding: "4px 10px",
                  borderRadius: "14px",
                  border: isSelected ? "1px solid #3b82f6" : "1px solid var(--border)",
                  background: isSelected ? "#1d4ed8" : "transparent",
                  color: isSelected ? "#fff" : "var(--fg)",
                  fontSize: "12px",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
              >
                {productName}
              </button>
            );
          }),
        )}
        {customMedicines
          .filter((m) => !medicineOptions.some((opt) => opt.yj_codes.includes(m.yj_code)))
          .map((m) => {
            const isSelected = selectedYjCodes.includes(m.yj_code);
            return (
              <button
                key={m.yj_code}
                type="button"
                onClick={() => onToggleYjCode(m.yj_code)}
                aria-pressed={isSelected}
                style={{
                  padding: "4px 10px",
                  borderRadius: "14px",
                  border: isSelected ? "1px solid #10b981" : "1px solid var(--border)",
                  background: isSelected ? "#065f46" : "transparent",
                  color: isSelected ? "#fff" : "var(--fg)",
                  fontSize: "12px",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
              >
                {isSelected ? "✓ " : "+ "}
                {m.name}
              </button>
            );
          })}
      </div>
      <div style={{ fontSize: "12px", color: "var(--muted)" }}>
        選択中: {selectedYjCodes.join(", ")}
      </div>
    </div>
  );
}
