import type { Metadata } from "next";
import { KeywordSearchScreen } from "../../features/keyword-search";

export const metadata: Metadata = {
  title: "添付文書キーワード検索 | medi-chat",
  description: "医療用医薬品の電子添文からキーワードで根拠を検索する",
};

export default function SearchPage() {
  return <KeywordSearchScreen />;
}
