import * as stylex from "@stylexjs/stylex";
import { useState } from "react";
import { ActionButton as Button } from "../../../../shared/component/ActionButton";
import { ChoiceChip as ToggleButton } from "../../../../shared/component/ChoiceChip";
import { styles } from "./KeywordSearchScreen.styles";
export interface MedicineSearchFilterProps {
  options: { id: string; label: string }[];
  selectedYjCodes: string[];
  onToggle: (id: string) => void;
  onClear: () => void;
}
export function MedicineSearchFilter({
  options,
  selectedYjCodes,
  onToggle,
  onClear,
}: MedicineSearchFilterProps) {
  const [showMedicineFilter, setShowMedicineFilter] = useState(false);
  return (
    <div {...stylex.props(styles.filterSection)}>
      <div {...stylex.props(styles.headerRow)}>
        <span {...stylex.props(styles.filterHeading)}>
          検索する医薬品:{" "}
          {selectedYjCodes.length === 0
            ? "登録済みの全製品"
            : `${selectedYjCodes.length}製品を選択中`}
        </span>
        <Button
          appearance="text"
          onActivate={() => setShowMedicineFilter((prev) => !prev)}
        >
          {showMedicineFilter ? "医薬品の選択を閉じる" : "医薬品を選んで絞り込む"}
        </Button>
      </div>
      <p>絞り込みを指定しない場合は、取り込み済みの全製品から検索します。</p>

      {showMedicineFilter && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 4 }}>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {options.map(({ id: code, label: name }) => (
              <ToggleButton
                key={code}
                selected={selectedYjCodes.includes(code)}
                onSelectedChange={() => onToggle(code)}
              >
                {name}
              </ToggleButton>
            ))}
          </div>
          {selectedYjCodes.length > 0 && (
            <div>
              <Button appearance="text" onActivate={() => onClear()}>
                すべての医薬品を対象に戻す（選択解除）
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
