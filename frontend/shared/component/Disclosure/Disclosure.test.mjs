import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { loadTestComponent } from "../../../scripts/load-test-component.mjs";

const { Disclosure } = await loadTestComponent(
  fileURLToPath(new URL("./Disclosure.tsx", import.meta.url)),
);

test("Disclosure exposes expanded content using a generic presentation variant", () => {
  const html = renderToStaticMarkup(
    createElement(
      Disclosure,
      { title: "Details", defaultOpen: true, variant: "accent" },
      "Content",
    ),
  );
  assert.match(html, /aria-expanded="true"/);
  assert.match(html, /Content/);
});
