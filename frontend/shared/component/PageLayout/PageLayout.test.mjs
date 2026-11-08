import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { loadTestComponent } from "../../../scripts/load-test-component.mjs";

const { PageLayout } = await loadTestComponent(
  fileURLToPath(new URL("./PageLayout.tsx", import.meta.url)),
);

test("PageLayout preserves screen identity and renders arbitrary page content", () => {
  const html = renderToStaticMarkup(
    createElement(PageLayout, { screen: "example" }, createElement("main", null, "Body")),
  );
  assert.match(html, /data-screen="example"/);
  assert.match(html, /<main>Body<\/main>/);
});
