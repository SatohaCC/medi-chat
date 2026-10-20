// Project display data from the same catalog as the backend; no second rule set.
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const catalog = JSON.parse(readFileSync(new URL("../backend/infrastructure/package_insert_definitions/package_insert_catalog.json", import.meta.url), "utf8"));
const rules = Object.values(catalog.intents)
  .filter((intent) => intent.keywords?.length)
  .sort((a, b) => a.keyword_priority - b.keyword_priority)
  .map((intent) => ({
    priority: intent.keyword_priority,
    keywords: intent.keywords.map((keyword) => keyword.text),
    sections: intent.sections.map((code) => ({ code, title: catalog.sections[code].title })),
  }));
const output = new URL("../frontend/features/search-guide/logicRules.json", import.meta.url);
const content = `${JSON.stringify(rules, null, 2)}\n`;
let current;
try {
  current = JSON.parse(readFileSync(output, "utf8"));
} catch (error) {
  if (error.code !== "ENOENT") throw error;
}
const matches = JSON.stringify(current) === JSON.stringify(rules);
if (process.argv.includes("--check")) {
  if (!matches) throw new Error("Regenerate search guide with node scripts/export-search-guide.mjs");
} else if (!matches) {
  writeFileSync(fileURLToPath(output), content);
}
