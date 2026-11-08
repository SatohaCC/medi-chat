import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { loadTestComponent } from "../../../../scripts/load-test-component.mjs";

const { KeywordSearchView } = await loadTestComponent(
  fileURLToPath(new URL("./KeywordSearchView.tsx", import.meta.url)),
);
test("keyword view renders initial, searching, empty and failure states without a router or API", () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = () => {
    throw new Error("A presentation must not fetch while rendering");
  };
  try {
    const props = {
      header: createElement("header", null, "テストヘッダー"),
      search: {
        query: "テスト検索",
        onQueryChange() {},
        isSearching: false,
        onSearch() {},
        isExpandEnabled: false,
        onExpansionChange() {},
      },
      medicineFilter: { options: [], selectedYjCodes: [], onToggle() {}, onClear() {} },
      result: {
        hasSearched: false,
        totalCount: 0,
        displayedSources: [],
        searchedQuery: "テスト検索",
        searchedExpandedKeywords: ["テスト類似語"],
        sectionGroups: [],
        selectedSection: "all",
        onSelectSection() {},
        searchWords: [],
        hasMedicineFilter: true,
      },
      error: null,
    };
    const render = (overrides = {}) =>
      renderToStaticMarkup(createElement(KeywordSearchView, { ...props, ...overrides }));
    assert.ok(render().includes("テストヘッダー"));
    assert.ok(!render().includes('aria-label="検索結果"'));
    assert.ok(
      render({ search: { ...props.search, isSearching: true } }).includes("検索中…"),
    );
    const empty = render({ result: { ...props.result, hasSearched: true } });
    assert.ok(empty.includes("0件"));
    assert.ok(empty.includes("テスト類似語"));
    assert.ok(empty.includes("選択を解除して検索範囲を広げられます"));
    assert.ok(render({ error: "テスト失敗" }).includes("テスト失敗"));
  } finally {
    globalThis.fetch = originalFetch;
  }
});
