import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";

const source = readFileSync(
  new URL("./SourceEvidenceContent.tsx", import.meta.url),
  "utf8",
);
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.ESNext },
});
// Resolve package imports before loading the actual TSX component as an ESM data URL.
const executable = outputText.replace(
  /from "([^"]+)"/g,
  (_, name) => `from ${JSON.stringify(import.meta.resolve(name))}`,
);
const { SourceEvidenceContent } = await import(
  `data:text/javascript;base64,${Buffer.from(executable).toString("base64")}`
);
const render = (content) =>
  renderToStaticMarkup(createElement(SourceEvidenceContent, { content }));

test("renders headings, table relationships, notes and escaped medical text", () => {
  const html = render(
    '### 対象製品\n\n<table><tr><td colspan="2">分類・頻度</td></tr>' +
      '<tr><td rowspan="2">消化器</td><td>悪心\n腹痛</td></tr>' +
      "<tr><td>頻度不明</td></tr></table>\n\n注）原文の注記。 CrCl &lt;30。",
  );
  assert.match(html, /<h3>対象製品<\/h3>/);
  assert.match(html, /colSpan="2"/);
  assert.match(html, /rowSpan="2"/);
  assert.match(html, /悪心\n腹痛/);
  assert.match(html, /注）原文の注記。 CrCl &lt;30/);
  assert.match(html, /class="source-table-scroll"/);
  assert.doesNotMatch(html, /&lt;table/);
});

test("removes scripts, event handlers, source styles and unsafe links", () => {
  const html = render(
    '<script>alert("x")</script><table onclick="alert(1)"><tr>' +
      '<td style="position:fixed" onmouseover="alert(2)">安全な本文</td></tr></table>' +
      '\n\n<a href="javascript:alert(3)">参照</a>',
  );
  assert.match(html, /安全な本文/);
  assert.doesNotMatch(html, /<script|alert\(|onclick|onmouseover|style=|javascript:/i);
});

test("renders the real 11.2 section as one table with category and frequency labels", () => {
  const rows = readFileSync(
    new URL(
      "../../../data_tools/structured/630004_3339003F5020_1_08/search_units.jsonl",
      import.meta.url,
    ),
    "utf8",
  )
    .trim()
    .split("\n")
    .map((line) => JSON.parse(line));
  const row = rows.find((item) => item.section.code === "11.2");
  assert.ok(row);
  const html = render(row.text);
  assert.equal((html.match(/<table>/g) || []).length, 1);
  assert.equal((html.match(/<tr>/g) || []).length, 34);
  assert.match(html, /精神神経系/);
  assert.match(html, /頻度不明/);
});
