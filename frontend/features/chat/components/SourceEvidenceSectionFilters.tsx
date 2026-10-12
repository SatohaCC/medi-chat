import * as stylex from "@stylexjs/stylex";
import { Button } from "../../../shared/ui/Button";
import type { SourceItem } from "../model/chat";
import { styles } from "./SourceEvidenceSectionFilters.styles";

export interface SourceSectionGroup {
  code: string;
  title: string;
  count: number;
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
  variant?: "plain" | "dashedBorder";
}

export function SourceEvidenceSectionFilters({
  sectionGroups,
  totalCount,
  selectedSection,
  onSelectSection,
  variant = "plain",
}: SourceEvidenceSectionFiltersProps) {
  if (sectionGroups.length <= 1) return null;

  const containerStyle =
    variant === "dashedBorder"
      ? [styles.sectionFilters, styles.dashedBorder]
      : [styles.sectionFilters];

  return (
    <div {...stylex.props(...containerStyle)}>
      <span {...stylex.props(styles.filterLabel)}>セクション別:</span>
      <Button
        variant="filterAll"
        selected={selectedSection === "all"}
        onActivate={() => onSelectSection("all")}
      >
        すべて ({totalCount})
      </Button>
      {sectionGroups.map((g) => {
        const isSelected = selectedSection === g.code;
        return (
          <Button
            key={g.code}
            variant="filterSection"
            selected={isSelected}
            onActivate={() => onSelectSection(isSelected ? "all" : g.code)}
          >
            [{g.code}] {g.title} ({g.count})
          </Button>
        );
      })}
    </div>
  );
}
