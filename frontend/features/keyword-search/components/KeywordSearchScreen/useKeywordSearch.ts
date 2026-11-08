import { useRef, useState } from "react";
import {
  extractHighlightWords,
  extractSectionGroups,
  type SourceItem,
} from "../../../chat";
import { useActiveMedicines } from "../../../medicine-selection/hooks/useActiveMedicines";
import { searchPackageInserts } from "../../api/searchApi";
import type { KeywordSearchViewProps } from "./KeywordSearchView";
/** Owns search execution, duplicate-send prevention and result snapshots. */
export function useKeywordSearch(): Omit<KeywordSearchViewProps, "header"> {
  const [query, setQuery] = useState("");
  const [selectedYjCodes, setSelectedYjCodes] = useState<string[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<SourceItem[] | null>(null);
  const [searchedQuery, setSearchedQuery] = useState("");
  const [selectedSection, setSelectedSection] = useState<string>("all");
  const [error, setError] = useState<string | null>(null);
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

  return {
    search: {
      query,
      onQueryChange: setQuery,
      isSearching,
      onSearch: () => {
        void handleSearch();
      },
      isExpandEnabled,
      onExpansionChange: setIsExpandEnabled,
    },
    medicineFilter: {
      options: activeMedicines.groups.flatMap((med) =>
        med.yj_codes.map((id, index) => ({
          id,
          label: med.brand_names[index] ?? med.generic_name,
        })),
      ),
      selectedYjCodes,
      onToggle: toggleYjCode,
      onClear: () => setSelectedYjCodes([]),
    },
    error,
    result: {
      hasSearched: results !== null,
      totalCount: sources.length,
      displayedSources,
      searchedQuery,
      searchedExpandedKeywords,
      sectionGroups,
      selectedSection,
      onSelectSection: setSelectedSection,
      searchWords,
      hasMedicineFilter: selectedYjCodes.length > 0,
    },
  };
}
