import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { loadTestComponent } from "../../../scripts/load-test-component.mjs";

const { Header } = await loadTestComponent(
  fileURLToPath(new URL("./Header.tsx", import.meta.url)),
);

test("Header renders supplied content without authentication, routes or domain data", () => {
  const html = renderToStaticMarkup(
    createElement(
      Header,
      {
        brand: createElement("h1", null, "Example workspace"),
        renderNavigation: () =>
          createElement("nav", { "aria-label": "Sections" }, "Overview"),
        actions: createElement("button", { type: "button" }, "Run"),
      },
      "Display options",
    ),
  );
  assert.match(html, /Example workspace/);
  assert.match(html, /Overview/);
  assert.match(html, /Display options/);
  assert.match(html, /Run/);
  assert.doesNotMatch(html, /ログアウト|医薬品|添付文書/);
});

for (const withControls of [false, true]) {
  test(`Header renders the supplied connection status with controls=${withControls}`, () => {
    const html = renderToStaticMarkup(
      createElement(
        Header,
        {
          brand: "Example workspace",
          renderNavigation: () => null,
          connectionStatus: createElement("span", { role: "status" }, "接続済み"),
        },
        withControls ? "Display options" : undefined,
      ),
    );
    assert.equal(html.match(/role="status"/g)?.length, 1);
    assert.match(html, /接続済み/);
    assert.equal(html.includes("Display options"), withControls);
  });
}
