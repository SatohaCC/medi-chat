"use client";
import { AppHeader } from "../../../app-shell/components/AppHeader";
import { KeywordSearchView } from "./KeywordSearchView";
import { useKeywordSearch } from "./useKeywordSearch";
export function KeywordSearchScreen() {
  return <KeywordSearchView {...useKeywordSearch()} header={<AppHeader />} />;
}
