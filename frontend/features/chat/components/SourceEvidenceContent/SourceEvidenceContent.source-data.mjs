import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { loadTestComponent } from "../../../../scripts/load-test-component.mjs";

const { SourceEvidenceContent } = await loadTestComponent(
  fileURLToPath(new URL("./SourceEvidenceContent.tsx", import.meta.url)),
);
const realSearchUnitsUrl = new URL(
  "../../../../../data/pmda/structured/630004_3339003F5020_1_08/search_units.jsonl",
  import.meta.url,
);

test("renders real registered source data when explicitly requested", () => {
  const units = readFileSync(realSearchUnitsUrl, "utf8")
    .trim()
    .split("\n")
    .map((line) => JSON.parse(line));
  const original = units.find((unit) => unit.section.code === "10.1");
  assert.ok(original, "The selected source data must contain section 10.1");
  const html = renderToStaticMarkup(
    createElement(SourceEvidenceContent, { content: original.text }),
  );
  assert.match(html, /<thead><tr><th>薬剤名等<\/th>/);
  assert.match(html, /イトラコナゾール/);
});
