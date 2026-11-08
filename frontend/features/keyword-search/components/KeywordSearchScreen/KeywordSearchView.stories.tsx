import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { S2ClientProvider } from "../../../../shared/providers/S2ClientProvider";
import { KeywordSearchView } from "./KeywordSearchView";

const meta = {
  title: "KeywordSearch/Presentation",
  component: KeywordSearchView,
  parameters: { layout: "fullscreen" },
  decorators: [
    (Story) => (
      <S2ClientProvider>
        <Story />
      </S2ClientProvider>
    ),
  ],
  args: {
    header: <header>テストヘッダー</header>,
    search: {
      query: "テスト検索",
      isSearching: false,
      isExpandEnabled: false,
      onQueryChange() {},
      onExpansionChange() {},
      onSearch() {},
    },
    medicineFilter: {
      options: [{ id: "test", label: "テスト対象" }],
      selectedYjCodes: [],
      onToggle() {},
      onClear() {},
    },
    result: {
      hasSearched: false,
      totalCount: 0,
      displayedSources: [],
      searchedQuery: "テスト検索",
      searchedExpandedKeywords: [],
      sectionGroups: [],
      selectedSection: "all",
      onSelectSection() {},
      searchWords: [],
      hasMedicineFilter: false,
    },
    error: null,
  },
} satisfies Meta<typeof KeywordSearchView>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Initial: Story = {};
export const Searching: Story = {
  args: { search: { ...meta.args.search, isSearching: true } },
};
export const Failed: Story = { args: { error: "テスト検索に失敗しました" } };
export const Empty: Story = {
  args: { result: { ...meta.args.result, hasSearched: true } },
};
