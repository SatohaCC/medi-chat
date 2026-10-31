"use client";

import { Button as S2Button } from "@react-spectrum/s2/Button";
import { Content, Heading, InlineAlert } from "@react-spectrum/s2/InlineAlert";
import { SearchField } from "@react-spectrum/s2/SearchField";
import * as stylex from "@stylexjs/stylex";
import { useRef, useState } from "react";
import { AppHeader } from "../../../shared/ui/AppHeader";
import { Button } from "../../../shared/ui/Button";
import { styles as layout } from "../../../shared/ui/PageLayout.styles";
import { ToggleButton } from "../../../shared/ui/ToggleButton";
import {
  extractHighlightWords,
  extractSectionGroups,
  SourceEvidenceCard,
  SourceEvidenceSectionFilters,
  type SourceItem,
} from "../../chat";
import { useActiveMedicines } from "../../medicine-selection/hooks/useActiveMedicines";
import { searchPackageInserts } from "../api/searchApi";
import { styles } from "./KeywordSearchScreen.styles";

export function KeywordSearchScreen() {
  const [query, setQuery] = useState("");
  const [selectedYjCodes, setSelectedYjCodes] = useState<string[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<SourceItem[] | null>(null);
  const [searchedQuery, setSearchedQuery] = useState("");
  const [selectedSection, setSelectedSection] = useState<string>("all");
  const [error, setError] = useState<string | null>(null);
  const [showMedicineFilter, setShowMedicineFilter] = useState(false);

  const searchBusy = useRef(false);
  const activeMedicines = useActiveMedicines();

  const toggleYjCode = (yjCode: string) => {
    setSelectedYjCodes((prev) =>
      prev.includes(yjCode) ? prev.filter((c) => c !== yjCode) : [...prev, yjCode],
    );
  };

  const handleSearch = async () => {
    if (searchBusy.current) return;
    const trimmed = query.trim();
    if (!trimmed) return;

    searchBusy.current = true;
    setIsSearching(true);
    setError(null);
    try {
      const data = await searchPackageInserts(trimmed, selectedYjCodes);
      setResults(data.items);
      setSearchedQuery(data.query);
      setSelectedSection("all");
    } catch (err) {
      setError(err instanceof Error ? err.message : "検索に失敗しました");
      setResults(null);
    } finally {
      searchBusy.current = false;
      setIsSearching(false);
    }
  };

  const searchWords = extractHighlightWords(searchedQuery);

  const sources = results ?? [];
  const sectionGroups = extractSectionGroups(sources);

  const displayedSources =
    selectedSection === "all"
      ? sources
      : sources.filter((s) => (s.section?.code || "other") === selectedSection);

  return (
    <div data-screen="keyword-search" {...stylex.props(layout.root)}>
      <AppHeader />
      <main {...stylex.props(styles.main)}>
        <div {...stylex.props(styles.headerRow)}>
          <div>
            <h1 {...stylex.props(styles.title)}>添付文書キーワード検索</h1>
            <p {...stylex.props(styles.description)}>
              登録済み添付文書からキーワードで直接根拠を検索・確認できます。
            </p>
          </div>
        </div>

        <form
          {...stylex.props(styles.searchForm)}
          onSubmit={(event) => event.preventDefault()}
        >
          <div {...stylex.props(styles.searchFieldSlot)}>
            <SearchField
              label="検索キーワード"
              value={query}
              onChange={setQuery}
              onSubmit={() => void handleSearch()}
              isDisabled={isSearching}
              placeholder="例: 悪心、併用禁忌、腎機能"
            />
          </div>
          <S2Button
            onPress={() => void handleSearch()}
            isDisabled={!query.trim()}
            isPending={isSearching}
          >
            {isSearching ? "検索中…" : "検索"}
          </S2Button>
        </form>

        <div {...stylex.props(styles.filterSection)}>
          <div {...stylex.props(styles.headerRow)}>
            <span {...stylex.props(styles.filterHeading)}>
              対象医薬品:{" "}
              {selectedYjCodes.length === 0
                ? "すべての医薬品（絞り込みなし）"
                : `${selectedYjCodes.length}製品を選択中`}
            </span>
            <Button
              variant="text"
              onActivate={() => setShowMedicineFilter((prev) => !prev)}
            >
              {showMedicineFilter ? "▲ 医薬品選択を閉じる" : "▼ 医薬品で絞り込む"}
            </Button>
          </div>

          {showMedicineFilter && (
            <div
              style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 4 }}
            >
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {activeMedicines.groups.flatMap((med) =>
                  med.yj_codes.map((code, idx) => {
                    const isSelected = selectedYjCodes.includes(code);
                    const name = med.brand_names[idx] ?? med.generic_name;
                    return (
                      <ToggleButton
                        key={code}
                        selected={isSelected}
                        onSelectedChange={() => toggleYjCode(code)}
                      >
                        {name}
                      </ToggleButton>
                    );
                  }),
                )}
              </div>
              {selectedYjCodes.length > 0 && (
                <div>
                  <Button variant="text" onActivate={() => setSelectedYjCodes([])}>
                    すべての医薬品を対象に戻す（選択解除）
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>

        {error && (
          <section aria-label="検索エラー">
            <InlineAlert variant="negative">
              <Heading>検索できませんでした</Heading>
              <Content>{error}</Content>
            </InlineAlert>
          </section>
        )}

        {results !== null && (
          <section
            aria-label="検索結果"
            style={{ display: "flex", flexDirection: "column", gap: 12 }}
          >
            <div {...stylex.props(styles.resultSummaryBar)}>
              <span {...stylex.props(styles.resultSummaryText)}>
                📄 「{searchedQuery}」の検索結果（合計：{sources.length}件）
              </span>
            </div>

            <SourceEvidenceSectionFilters
              sectionGroups={sectionGroups}
              totalCount={sources.length}
              selectedSection={selectedSection}
              onSelectSection={setSelectedSection}
            />

            {displayedSources.length === 0 ? (
              <div {...stylex.props(styles.empty)}>
                該当する添付文書の根拠記載は見つかりませんでした（0件）
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
      </main>
    </div>
  );
}
