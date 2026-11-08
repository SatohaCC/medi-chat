import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { loadTestComponent } from "../../../scripts/load-test-component.mjs";

const { MarkdownContent } = await loadTestComponent(
  fileURLToPath(new URL("./MarkdownContent.tsx", import.meta.url)),
);

test("shared text rendering escapes markup, links safely and treats highlight terms literally", () => {
  const markdown = renderToStaticMarkup(
    createElement(MarkdownContent, {
      content: "[Example](https://example.test)\n\n<script>alert(1)</script>",
    }),
  );
  assert.match(markdown, /rel="noopener noreferrer"/);
  assert.doesNotMatch(markdown, /<script>/);
});
