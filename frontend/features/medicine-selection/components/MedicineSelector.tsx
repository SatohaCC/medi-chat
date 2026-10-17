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
  const registeredYjCodes = new Set(medicineOptions.flatMap((m) => m.yj_codes));
  const unregisteredSelected = customMedicines.filter(
    (m) => selectedYjCodes.includes(m.yj_code) && !registeredYjCodes.has(m.yj_code),
  );
  const registeredSelectedCount = selectedYjCodes.filter((code) =>
    registeredYjCodes.has(code),
  ).length;

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
            const isRegistered = registeredYjCodes.has(m.yj_code);
            return (
              <ToggleButton
                key={m.yj_code}
                selected={isSelected}
                onSelectedChange={() => onToggleYjCode(m.yj_code)}
                variant={isRegistered ? "custom" : "unregistered"}
              >
                {isSelected ? "✓ " : "+ "}
                {m.name}
                {!isRegistered && (
                  <span {...stylex.props(styles.unregisteredTag)}>（対象外）</span>
                )}
              </ToggleButton>
            );
          })}
      </div>

      {unregisteredSelected.length > 0 && (
        <div {...stylex.props(styles.unregisteredAlert)} role="status">
          <span {...stylex.props(styles.alertIcon)}>⚠️</span>
          <div {...stylex.props(styles.alertContent)}>
            <span {...stylex.props(styles.alertTitle)}>
              検索対象外（電子添文未登録）:
            </span>{" "}
            {unregisteredSelected.map((m) => m.name).join("、 ")}
            <div {...stylex.props(styles.alertDesc)}>
              ※
              電子添文データが未登録のため、添付文書の検索・根拠引用は行われません（登録済み医薬品のみで検索・回答します）。
            </div>
          </div>
        </div>
      )}

      <div {...stylex.props(styles.selectionSummary)}>
        選択中: {selectedYjCodes.join(", ")}
        {unregisteredSelected.length > 0 && (
          <span {...stylex.props(styles.unregisteredSummary)}>
            {" "}
            (検索対象: {registeredSelectedCount}件 / 対象外: {unregisteredSelected.length}
            件)
          </span>
        )}
      </div>
    </div>
  );
}
