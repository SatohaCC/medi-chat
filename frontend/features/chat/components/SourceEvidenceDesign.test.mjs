import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { loadTestComponent } from "../../../scripts/load-test-component.mjs";

const { SourceEvidenceCard } = await loadTestComponent(
  fileURLToPath(new URL("./SourceEvidenceCard.tsx", import.meta.url)),
);
const { SourceEvidencePanel } = await loadTestComponent(
  fileURLToPath(new URL("./SourceEvidencePanel.tsx", import.meta.url)),
);
const { MessageItem } = await loadTestComponent(
  fileURLToPath(new URL("./MessageItem.tsx", import.meta.url)),
);

const source = {
  unit_id: "unit-1",
  document_id: "document-1",
  product_name: "対象製品",
  generic_name: "対象成分",
  product_yj_codes: ["1234567A1000"],
  document_revision: { year_month: "2026-10", version: "第2版" },
  section: { code: "10.1", title: "併用禁忌" },
  kind: "interaction_row",
  excerpt: "原文の条件と注記を保持する。",
  columns: {
    drug_name: "相手薬A\n相手薬B",
    clinical_symptoms_and_measures: "原文に記載された措置。",
    mechanism_and_risk_factors: "原文に記載された機序。",
  },
  references: [
    {
      kind: "参照",
      target_section_code: "9.2",
      target_url: "https://example.invalid/ref",
    },
  ],
  url: "https://example.invalid/source",
  retrieved_by: ["logic", "jev"],
};
const render = (overrides = {}, highlightWords) =>
  renderToStaticMarkup(
    createElement(SourceEvidenceCard, {
      source: { ...source, ...overrides },
      highlightWords,
    }),
  );

test("product labels never highlight medicine names while clinical headings still highlight", () => {
  const html = render({}, ["対象製品", "併用禁忌"]);
  assert.ok(html.includes("対象製品"));
  assert.doesNotMatch(html, /<mark[^>]*>対象製品<\/mark>/);
  assert.match(html, /<mark[^>]*>併用禁忌<\/mark>/);
});

test("interaction design preserves source columns, notes and provenance without clinical inference", () => {
  const html = render();
  assert.match(html, /data-evidence-design="InteractionEvidence"/);
  assert.match(html, /<thead><tr>/);
  for (const label of ["薬剤名等", "臨床症状・措置方法", "機序・危険因子"]) {
    assert.ok(html.includes(label));
  }
  assert.equal((html.match(/scope="col"/g) ?? []).length, 3);
  for (const text of [
    "対象製品",
    "[10.1] 併用禁忌",
    "相手薬A\n相手薬B",
    "原文に記載された措置。",
    "原文に記載された機序。",
    "原文の条件と注記を保持する。",
    "2026-10 / 第2版",
    "1234567A1000",
  ])
    assert.ok(html.includes(text), text);
  assert.match(html, /href="https:\/\/example.invalid\/source"/);
  assert.match(html, /href="https:\/\/example.invalid\/ref"/);
  assert.doesNotMatch(html, /本剤の投与は禁忌|代替薬|休薬|指導記録を確定|CYP/);
});

test("missing and unknown columns never discard available evidence or invent missing fields", () => {
  const partial = render({
    columns: { drug_name: "相手薬", additional_note: "追加の原文" },
  });
  assert.match(partial, /追加の原文/);
  assert.doesNotMatch(partial, /機序・危険因子|CYP/);
  for (const columns of [null, {}, { drug_name: " " }]) {
    assert.match(render({ columns }), /原文の条件と注記を保持する。/);
  }
});

test("dosage preserves table spans, patient conditions and safety sanitization", () => {
  const html = render({
    kind: "section",
    columns: null,
    section: { code: "6.1", title: "用法及び用量" },
    excerpt:
      '<table><tr><th colspan="2">成人の場合</th></tr><tr><td rowspan="2">条件付き</td><td>原文の用量</td></tr><tr><td>原文の例外</td></tr></table>\n\n注）腎機能に応じて調整。<script>alert(1)</script>',
  });
  assert.match(html, /data-evidence-design="DosageEvidence"/);
  assert.match(html, /colSpan="2"/);
  assert.match(html, /rowSpan="2"/);
  assert.match(html, /成人の場合/);
  assert.match(html, /原文の例外/);
  assert.match(html, /注）腎機能に応じて調整。/);
  assert.doesNotMatch(html, /<script|alert\(/);
});

test("precautions retain every original item and do not become a completion checklist", () => {
  const excerpt = Array.from(
    { length: 8 },
    (_, i) => `- 確認事項${i + 1}を省略しないこと。`,
  ).join("\n");
  const html = render({
    kind: "section",
    columns: null,
    section: { code: "14.1", title: "適用上の注意" },
    excerpt,
  });
  assert.match(html, /data-evidence-design="PrecautionEvidence"/);
  assert.match(html, /確認事項8を省略しないこと。/);
  assert.doesNotMatch(html, /type="checkbox"|指導記録|必須確認/);
});

test("section families select designs exactly and unknown sections retain full original text", () => {
  for (const [code, design] of [
    ["10.2", "InteractionEvidence"],
    ["7.1", "DosageEvidence"],
    ["8", "PrecautionEvidence"],
    ["4", "TextEvidence"],
    ["100", "TextEvidence"],
    ["80", "TextEvidence"],
    ["140", "TextEvidence"],
  ]) {
    const html = render({
      kind: "section",
      columns: null,
      section: { code, title: "原文の見出し" },
    });
    assert.ok(html.includes(`data-evidence-design="${design}"`), code);
    assert.match(html, /原文の条件と注記を保持する。/);
  }
});

test("search highlights survive the source design", () => {
  const html = render({}, ["相手薬A"]);
  assert.match(html, /<mark class="search-highlight">相手薬A<\/mark>/);
});

test("assistant answer keeps Markdown and ignores obsolete generated clinical UI", () => {
  const html = renderToStaticMarkup(
    createElement(MessageItem, {
      message: {
        role: "assistant",
        content: "**通常の回答**",
        sources: [source],
        uiSpec: {
          root: "old",
          elements: {
            old: {
              type: "ContraindicationCard",
              props: { primaryDrug: "表示してはいけないカード" },
            },
          },
        },
      },
      isStreaming: false,
      isLast: true,
    }),
  );
  assert.match(html, /<strong>通常の回答<\/strong>/);
  assert.doesNotMatch(
    html,
    /表示してはいけないカード|data-evidence-design|data-genui-renderer/,
  );
});

test("always retrieved evidence keeps both the safety and question-based reasons", () => {
  const html = render({
    section: { code: "8", title: "重要な基本的注意" },
    retrieved_by: ["always", "logic"],
  });
  assert.ok(html.includes("常時取得"));
  assert.ok(html.includes("ロジック取得"));
  assert.ok(html.includes("重要な基本的注意"));
});

test("progressive panel distinguishes always retrieved evidence from logic hits", () => {
  const html = renderToStaticMarkup(
    createElement(SourceEvidencePanel, {
      sources: [{ ...source, retrieved_by: ["always", "logic"] }],
      retrievalStatus: "jev_searching",
    }),
  );
  assert.ok(html.includes("常時取得：1件"));
  assert.ok(html.includes("ロジック：1件"));
  assert.ok(html.includes("合計：1件"));
  assert.ok(html.includes("質問内容にかかわらず"));
  assert.ok(html.includes("取得理由別の件数には重複"));
  assert.ok(!html.includes("ロジック検索根拠"));
});
