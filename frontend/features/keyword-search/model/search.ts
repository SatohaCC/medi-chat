import type { SourceItem } from "../../chat";

export interface KeywordSearchResponse {
  query: string;
  items: SourceItem[];
  total_count: number;
}
