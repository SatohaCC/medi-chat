import * as stylex from "@stylexjs/stylex";
import { ChoiceChip as ToggleButton } from "../../../../shared/component/ChoiceChip";
import type { SourceItem } from "../../model/chat";
import { styles } from "./SourceEvidenceSectionFilters.styles";

export interface SourceSectionGroup {
  code: string;
  title: string;
  count: number;
}

export interface SourceMedicineGroup {
  name: string;
  count: number;
}

export function extractMedicineGroups(sources: SourceItem[]): SourceMedicineGroup[] {
  const medicineNamesInOrder: string[] = [];
  const medicineMap = new Map<string, SourceMedicineGroup>();
  for (const s of sources) {
    const name = s.product_name || s.generic_name || "その他";
    const existing = medicineMap.get(name);
    if (existing) {
      existing.count += 1;
    } else {
      medicineNamesInOrder.push(name);
      medicineMap.set(name, { name, count: 1 });
    }
  }
  return medicineNamesInOrder
    .map((name) => medicineMap.get(name))
    .filter((g): g is SourceMedicineGroup => g !== undefined);
}

export function extractSectionGroups(sources: SourceItem[]): SourceSectionGroup[] {
  const sectionCodesInOrder: string[] = [];
  const sectionMap = new Map<string, SourceSectionGroup>();
  for (const s of sources) {
    const code = s.section?.code || "other";
    const title = s.section?.title || "";
    const existing = sectionMap.get(code);
    if (existing) {
      existing.count += 1;
    } else {
      sectionCodesInOrder.push(code);
      sectionMap.set(code, { code, title, count: 1 });
    }
  }
  return sectionCodesInOrder
    .map((code) => sectionMap.get(code))
    .filter((g): g is SourceSectionGroup => g !== undefined);
}

export interface SourceEvidenceSectionFiltersProps {
  sectionGroups: SourceSectionGroup[];
  totalCount: number;
  selectedSection: string;
  onSelectSection: (sectionCode: string) => void;
  medicineGroups?: SourceMedicineGroup[];
  selectedMedicine?: string;
  onSelectMedicine?: (medicineName: string) => void;
  variant?: "plain" | "dashedBorder";
}

export function SourceEvidenceSectionFilters({
  sectionGroups,
  totalCount,
  selectedSection,
  onSelectSection,
  medicineGroups,
  selectedMedicine = "all",
  onSelectMedicine,
  variant = "plain",
}: SourceEvidenceSectionFiltersProps) {
  const hasMultipleMedicines = Boolean(medicineGroups && medicineGroups.length > 1);
  const hasMultipleSections = sectionGroups.length > 1;

  if (!hasMultipleMedicines && !hasMultipleSections) return null;

  const containerStyle =
    variant === "dashedBorder"
      ? [styles.filterContainer, styles.dashedBorder]
      : [styles.filterContainer];

  return (
    <div {...stylex.props(...containerStyle)}>
      {hasMultipleMedicines && (
        <div {...stylex.props(styles.filterRow)}>
          <span {...stylex.props(styles.filterLabel)}>医薬品別:</span>
          <ToggleButton
            appearance="chip"
            selected={selectedMedicine === "all"}
            onSelectedChange={() => onSelectMedicine?.("all")}
          >
            すべて ({totalCount})
          </ToggleButton>
          {medicineGroups?.map((g) => {
            const isSelected = selectedMedicine === g.name;
            return (
              <ToggleButton
                key={g.name}
                appearance="mutedChip"
                selected={isSelected}
                onSelectedChange={() => onSelectMedicine?.(isSelected ? "all" : g.name)}
              >
                {g.name} ({g.count})
              </ToggleButton>
            );
          })}
        </div>
      )}

      {hasMultipleSections && (
        <div {...stylex.props(styles.filterRow)}>
          <span {...stylex.props(styles.filterLabel)}>セクション別:</span>
          <ToggleButton
            appearance="chip"
            selected={selectedSection === "all"}
            onSelectedChange={() => onSelectSection("all")}
          >
            すべて ({totalCount})
          </ToggleButton>
          {sectionGroups.map((g) => {
            const isSelected = selectedSection === g.code;
            return (
              <ToggleButton
                key={g.code}
                appearance="subtleChip"
                selected={isSelected}
                onSelectedChange={() => onSelectSection(isSelected ? "all" : g.code)}
              >
                [{g.code}] {g.title} ({g.count})
              </ToggleButton>
            );
          })}
        </div>
      )}
    </div>
  );
}
