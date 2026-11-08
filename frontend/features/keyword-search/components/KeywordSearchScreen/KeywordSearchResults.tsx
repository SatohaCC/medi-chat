import * as stylex from "@stylexjs/stylex";
import {
  SourceEvidenceCard,
  SourceEvidenceSectionFilters,
  type SourceItem,
} from "../../../chat";
import type { SourceSectionGroup } from "../../../chat/components/SourceEvidenceSectionFilters";
import { styles } from "./KeywordSearchScreen.styles";
export interface KeywordSearchResultsProps {
  hasSearched: boolean;
  totalCount: number;
  displayedSources: SourceItem[];
  searchedQuery: string;
  searchedExpandedKeywords: string[];
  sectionGroups: SourceSectionGroup[];
  selectedSection: string;
  onSelectSection: (value: string) => void;
  searchWords: string[];
  hasMedicineFilter: boolean;
}
export function KeywordSearchResults({
  hasSearched,
  totalCount,
  displayedSources,
  searchedQuery,
  searchedExpandedKeywords,
  sectionGroups,
  selectedSection,
  onSelectSection,
  searchWords,
  hasMedicineFilter,
}: KeywordSearchResultsProps) {
  return (
    <>
      {hasSearched && (
        <section
          aria-label="検索結果"
          style={{ display: "flex", flexDirection: "column", gap: 12 }}
        >
          <div {...stylex.props(styles.resultSummaryBar)}>
            <span {...stylex.props(styles.resultSummaryText)}>
              📄 「{searchedQuery}」の検索結果（合計：{totalCount}件）
            </span>
          </div>

          {searchedExpandedKeywords.length > 0 && (
            <div {...stylex.props(styles.expandedKeywordsBadge)}>
              <span {...stylex.props(styles.expandedLabel)}>🔍 検索に含めた類似語:</span>
              {searchedExpandedKeywords.map((word) => (
                <span key={word} {...stylex.props(styles.keywordTag)}>
                  {word}
                </span>
              ))}
            </div>
          )}

          <SourceEvidenceSectionFilters
            sectionGroups={sectionGroups}
            totalCount={totalCount}
            selectedSection={selectedSection}
            onSelectSection={onSelectSection}
          />

          {displayedSources.length === 0 ? (
            <div {...stylex.props(styles.empty)}>
              <strong>該当する記載は見つかりませんでした（0件）</strong>
              <span>
                検索語を短くするか、別の表現を試してください。
                {hasMedicineFilter &&
                  " 医薬品を絞り込んでいる場合は、選択を解除して検索範囲を広げられます。"}
              </span>
            </div>
          ) : (
            <div {...stylex.props(styles.resultsList)}>
              {displayedSources.map((s) => (
                <SourceEvidenceCard
                  key={s.unit_id}
                  source={s}
                  highlightWords={searchWords}
                />
              ))}
            </div>
          )}
        </section>
      )}
    </>
  );
}
