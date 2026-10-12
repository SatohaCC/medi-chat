import * as stylex from "@stylexjs/stylex";
import { ToggleButton } from "../../../shared/ui/ToggleButton";
import type {
  CustomMedicine,
  MedicineCatalogStatus,
  MedicineOption,
} from "../model/medicine";
import { styles } from "./MedicineSelector.styles";

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
    <div {...stylex.props(styles.root)}>
      <div {...stylex.props(styles.label)}>対象医薬品（YJコードで特定・複数選択可）:</div>
      {medicineCatalogStatus === "loading" && (
        <div {...stylex.props(styles.loading)}>対応医薬品を読み込み中…</div>
      )}
      {medicineCatalogStatus === "error" && (
        <div {...stylex.props(styles.error)}>
          対応医薬品を取得できませんでした。バックエンドとの接続を確認してください。
        </div>
      )}
      <div {...stylex.props(styles.products)}>
        {medicineOptions.flatMap((medicine) =>
          medicine.yj_codes.map((yjCode, index) => {
            const isSelected = selectedYjCodes.includes(yjCode);
            const productName =
              medicine.brand_names[index] ??
              medicine.brand_names[0] ??
              medicine.generic_name;
            return (
              <ToggleButton
                key={yjCode}
                selected={isSelected}
                onSelectedChange={() => onToggleYjCode(yjCode)}
              >
                {productName}
              </ToggleButton>
            );
          }),
        )}
        {customMedicines
          .filter((m) => !medicineOptions.some((opt) => opt.yj_codes.includes(m.yj_code)))
          .map((m) => {
            const isSelected = selectedYjCodes.includes(m.yj_code);
            return (
              <ToggleButton
                key={m.yj_code}
                selected={isSelected}
                onSelectedChange={() => onToggleYjCode(m.yj_code)}
                variant="custom"
              >
                {isSelected ? "✓ " : "+ "}
                {m.name}
              </ToggleButton>
            );
          })}
      </div>
      <div {...stylex.props(styles.selectionSummary)}>
        選択中: {selectedYjCodes.join(", ")}
      </div>
    </div>
  );
}
