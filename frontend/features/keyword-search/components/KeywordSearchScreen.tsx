"use client";

import { Button as S2Button } from "@react-spectrum/s2/Button";
import { Content, Heading, InlineAlert } from "@react-spectrum/s2/InlineAlert";
import { SearchField } from "@react-spectrum/s2/SearchField";
import { Switch } from "@react-spectrum/s2/Switch";
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

const queryExamples = ["悪心", "併用禁忌", "腎機能障害"];

export function KeywordSearchScreen() {
  const [query, setQuery] = useState("");
  const [selectedYjCodes, setSelectedYjCodes] = useState<string[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<SourceItem[] | null>(null);
  const [searchedQuery, setSearchedQuery] = useState("");
  const [selectedSection, setSelectedSection] = useState<string>("all");
  const [error, setError] = useState<string | null>(null);
  const [showMedicineFilter, setShowMedicineFilter] = useState(false);
  const [isExpandEnabled, setIsExpandEnabled] = useState(false);
  const [searchedExpandedKeywords, setSearchedExpandedKeywords] = useState<string[]>([]);

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
      const data = await searchPackageInserts(trimmed, selectedYjCodes, isExpandEnabled);
      setResults(data.items);
      setSearchedQuery(data.query);
      setSearchedExpandedKeywords(data.expanded_keywords ?? []);
      setSelectedSection("all");
    } catch (err) {
      setError(err instanceof Error ? err.message : "検索に失敗しました");
      setResults(null);
      setSearchedExpandedKeywords([]);
    } finally {
      searchBusy.current = false;
      setIsSearching(false);
    }
  };

  const searchWords = extractHighlightWords(
    [searchedQuery, ...searchedExpandedKeywords].join(" "),
  );

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
          <div {...stylex.props(styles.searchBarRow)}>
            <div {...stylex.props(styles.searchFieldSlot)}>
              <SearchField
                label="検索キーワード"
                value={query}
                onChange={setQuery}
                onSubmit={() => void handleSearch()}
                isDisabled={isSearching}
                aria-describedby="keyword-search-help"
                placeholder="キーワードを入力"
              />
            </div>
            <S2Button
              onPress={() => void handleSearch()}
              isDisabled={!query.trim()}
              isPending={isSearching}
            >
              {isSearching ? "検索中…" : "検索"}
            </S2Button>
          </div>
          <div id="keyword-search-help" {...stylex.props(styles.exampleRow)}>
            <span {...stylex.props(styles.exampleText)}>
              例を選ぶと検索欄に入力されます。例:
            </span>
            <div {...stylex.props(styles.exampleChips)}>
              {queryExamples.map((example) => (
                <button
                  key={example}
                  type="button"
                  disabled={isSearching}
                  {...stylex.props(
                    styles.exampleChip,
                    isSearching && styles.exampleChipDisabled,
                  )}
                  onClick={() => setQuery(example)}
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
          <div {...stylex.props(styles.optionsRow)}>
            <Switch
              isSelected={isExpandEnabled}
              onChange={setIsExpandEnabled}
              isDisabled={isSearching}
              size="L"
              isEmphasized
            >
              関連する表現も検索
            </Switch>
            <span {...stylex.props(styles.expansionNote)}>
              例：「吐き気」と入力すると「悪心」「嘔吐」も検索します。
            </span>
          </div>
        </form>

        <div {...stylex.props(styles.filterSection)}>
          <div {...stylex.props(styles.headerRow)}>
            <span {...stylex.props(styles.filterHeading)}>
              検索する医薬品:{" "}
              {selectedYjCodes.length === 0
                ? "登録済みの全製品"
                : `${selectedYjCodes.length}製品を選択中`}
            </span>
            <Button
              variant="text"
              onActivate={() => setShowMedicineFilter((prev) => !prev)}
            >
              {showMedicineFilter ? "医薬品の選択を閉じる" : "医薬品を選んで絞り込む"}
            </Button>
          </div>
          <p>絞り込みを指定しない場合は、取り込み済みの全製品から検索します。</p>

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

            {searchedExpandedKeywords.length > 0 && (
              <div {...stylex.props(styles.expandedKeywordsBadge)}>
                <span {...stylex.props(styles.expandedLabel)}>
                  🔍 検索に含めた類似語:
                </span>
                {searchedExpandedKeywords.map((word) => (
                  <span key={word} {...stylex.props(styles.keywordTag)}>
                    {word}
                  </span>
                ))}
              </div>
            )}

            <SourceEvidenceSectionFilters
              sectionGroups={sectionGroups}
              totalCount={sources.length}
              selectedSection={selectedSection}
              onSelectSection={setSelectedSection}
            />

            {displayedSources.length === 0 ? (
              <div {...stylex.props(styles.empty)}>
                <strong>該当する記載は見つかりませんでした（0件）</strong>
                <span>
                  検索語を短くするか、別の表現を試してください。
                  {selectedYjCodes.length > 0 &&
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
      </main>
    </div>
  );
}
