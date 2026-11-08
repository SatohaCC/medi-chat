import * as stylex from "@stylexjs/stylex";
import { ActionButton as S2Button } from "../../../../shared/component/ActionButton";
import { SearchInput as SearchField } from "../../../../shared/component/SearchInput";
import { SwitchControl as Switch } from "../../../../shared/component/SwitchControl";
import { styles } from "./KeywordSearchScreen.styles";

const queryExamples = ["悪心", "併用禁忌", "腎機能障害"];
export interface KeywordSearchFormProps {
  query: string;
  onQueryChange: (value: string) => void;
  isSearching: boolean;
  onSearch: () => void;
  isExpandEnabled: boolean;
  onExpansionChange: (value: boolean) => void;
}
export function KeywordSearchForm({
  query,
  onQueryChange,
  isSearching,
  onSearch,
  isExpandEnabled,
  onExpansionChange,
}: KeywordSearchFormProps) {
  return (
    <form
      {...stylex.props(styles.searchForm)}
      onSubmit={(event) => event.preventDefault()}
    >
      <div {...stylex.props(styles.searchBarRow)}>
        <div {...stylex.props(styles.searchFieldSlot)}>
          <SearchField
            label="検索キーワード"
            value={query}
            onChange={onQueryChange}
            onSubmit={() => void onSearch()}
            disabled={isSearching}
            descriptionId="keyword-search-help"
            placeholder="キーワードを入力"
          />
        </div>
        <S2Button
          onActivate={() => void onSearch()}
          disabled={!query.trim()}
          pending={isSearching}
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
              onClick={() => onQueryChange(example)}
            >
              {example}
            </button>
          ))}
        </div>
      </div>
      <div {...stylex.props(styles.optionsRow)}>
        <Switch
          selected={isExpandEnabled}
          onChange={onExpansionChange}
          disabled={isSearching}
        >
          関連する表現も検索
        </Switch>
        <span {...stylex.props(styles.expansionNote)}>
          例：「吐き気」と入力すると「悪心」「嘔吐」も検索します。
        </span>
      </div>
    </form>
  );
}
