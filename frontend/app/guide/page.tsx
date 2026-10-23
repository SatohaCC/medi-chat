import type { Metadata } from "next";
import { SearchGuideScreen } from "../../features/search-guide";

export const metadata: Metadata = {
  title: "検索の仕組み | medi-chat",
  description:
    "警告・禁忌・重要な基本的注意の常時取得と、ロジック検索・形態素解析・Jev判定による根拠の追加を説明します。",
};

export default function GuidePage() {
  return <SearchGuideScreen />;
}
