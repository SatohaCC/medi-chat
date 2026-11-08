import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { loadTestComponent } from "../../../scripts/load-test-component.mjs";

const { HighlightText } = await loadTestComponent(
  fileURLToPath(new URL("./HighlightText.tsx", import.meta.url)),
);
test("highlight terms are matched literally", () => {
  const highlight = renderToStaticMarkup(
    createElement(HighlightText, { text: "A+B and plain", words: ["A+B"] }),
  );
  assert.match(highlight, /<mark[^>]*>A\+B<\/mark> and plain/);
});
