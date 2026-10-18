import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { loadTestComponent } from "../../../scripts/load-test-component.mjs";

const { ExpandableEvidenceContent } = await loadTestComponent(
  fileURLToPath(new URL("./ExpandableEvidenceContent.tsx", import.meta.url)),
);

const render = (props) =>
  renderToStaticMarkup(createElement(ExpandableEvidenceContent, props));

test("alwaysExpanded=true renders full content without toggle buttons", () => {
  const content =
    "1. 警告\n\n本剤の投与は、緊急時に十分対応できる医療施設において実施すること。";
  const html = render({ content, alwaysExpanded: true });
  assert.ok(
    html.includes("本剤の投与は、緊急時に十分対応できる医療施設において実施すること。"),
  );
  assert.ok(!html.includes("続きを読む"));
  assert.ok(!html.includes("折りたたむ"));
});

test("expandable content preserves all text and highlights matching words", () => {
  const content =
    "用法及び用量\n\n通常、成人にはリバーロキサバンとして15mgを1日1回食後に経口投与する。";
  const html = render({
    content,
    highlightWords: ["リバーロキサバン", "15mg"],
    alwaysExpanded: false,
  });
  assert.ok(html.includes("通常、成人には"));
  assert.match(html, /<mark class="search-highlight">リバーロキサバン<\/mark>/);
  assert.match(html, /<mark class="search-highlight">15mg<\/mark>/);
});

test("warning and contraindication designs remain always expanded through SourceEvidenceDesign", async () => {
  const { SourceEvidenceCard } = await loadTestComponent(
    fileURLToPath(new URL("./SourceEvidenceCard.tsx", import.meta.url)),
  );

  const warningSource = {
    unit_id: "w-1",
    document_id: "doc-1",
    product_name: "イグザレルト錠15mg",
    generic_name: "リバーロキサバン",
    product_yj_codes: ["3339003F5020"],
    document_revision: { year_month: "2026-10", version: "第2版" },
    section: { code: "1", title: "警告" },
    kind: "section",
    excerpt: "極めて重要な警告記載。全開で表示されなければならない。",
    columns: null,
    references: [],
    url: "https://example.invalid/source",
    retrieved_by: ["logic"],
  };

  const html = renderToStaticMarkup(
    createElement(SourceEvidenceCard, { source: warningSource }),
  );
  assert.ok(html.includes("極めて重要な警告記載。全開で表示されなければならない。"));
  assert.ok(!html.includes("続きを読む"));
  assert.match(html, /data-evidence-design="WarningEvidence"/);
});
