import * as stylex from "@stylexjs/stylex";
import type { ReactNode } from "react";
import { Notice } from "../../../../shared/component/Notice";
import { PageLayout } from "../../../../shared/component/PageLayout";
import { KeywordSearchForm, type KeywordSearchFormProps } from "./KeywordSearchForm";
import {
  KeywordSearchResults,
  type KeywordSearchResultsProps,
} from "./KeywordSearchResults";
import { styles } from "./KeywordSearchScreen.styles";
import {
  MedicineSearchFilter,
  type MedicineSearchFilterProps,
} from "./MedicineSearchFilter";
export interface KeywordSearchViewProps {
  header: ReactNode;
  search: KeywordSearchFormProps;
  medicineFilter: MedicineSearchFilterProps;
  error: string | null;
  result: KeywordSearchResultsProps;
}
export function KeywordSearchView({
  header,
  search,
  medicineFilter,
  error,
  result,
}: KeywordSearchViewProps) {
  return (
    <PageLayout screen="keyword-search">
      {header}
      <main {...stylex.props(styles.main)}>
        <div {...stylex.props(styles.headerRow)}>
          <div>
            <h1 {...stylex.props(styles.title)}>添付文書キーワード検索</h1>
            <p {...stylex.props(styles.description)}>
              登録済み添付文書からキーワードで直接根拠を検索・確認できます。
            </p>
          </div>
        </div>

        <KeywordSearchForm {...search} />
        <MedicineSearchFilter {...medicineFilter} />
        {error && (
          <section aria-label="検索エラー">
            <Notice title="検索できませんでした">{error}</Notice>
          </section>
        )}
        <KeywordSearchResults {...result} />
      </main>
    </PageLayout>
  );
}
