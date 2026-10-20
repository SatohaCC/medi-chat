import type { Metadata } from "next";
import { SearchGuideScreen } from "../../features/search-guide";

export const metadata: Metadata = {
  title: "検索の仕組み | medi-chat",
  description: "ロジック検索・形態素解析・Jev判定による添付文書の根拠取得を説明します。",
};

export default function GuidePage() {
  return <SearchGuideScreen />;
}
