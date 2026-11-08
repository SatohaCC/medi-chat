import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { loadTestComponent } from "../../../scripts/load-test-component.mjs";

const { Tabs } = await loadTestComponent(
  fileURLToPath(new URL("./Tabs.tsx", import.meta.url)),
);

test("Tabs renders the supplied selected panel and accessible labels", () => {
  const html = renderToStaticMarkup(
    createElement(Tabs, {
      value: "second",
      onValueChange() {},
      label: "表示切り替え",
      items: [
        { id: "first", title: "概要", content: "概要の内容" },
        { id: "second", title: "補足", content: "補足の内容" },
      ],
    }),
  );
  assert.match(html, /role="tablist"/);
  assert.match(html, /aria-label="表示切り替え"/);
  assert.match(html, /補足の内容/);
  assert.doesNotMatch(html, /概要の内容/);
});
