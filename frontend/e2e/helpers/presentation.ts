import type { SourceItem } from "../../features/chat/model/chat";
export const visualSource: SourceItem = {
  unit_id: "visual-section",
  document_id: "visual-document",
  product_name: "テスト医薬品A",
  generic_name: "テスト成分",
  product_yj_codes: ["3339003F5020"],
  document_revision: { source_label: "今回", year_month: "2026-10", version: "1" },
  section: { code: "11.2", title: "その他の副作用" },
  kind: "section",
  excerpt:
    '### 原文の見出し\n\n<table><tr><th scope="col" colspan="2">分類・頻度</th><th scope="col">頻度不明</th></tr><tr><td rowspan="2">消化器</td><td>悪心 腹痛</td><td>右端の医学原文</td></tr><tr><td>CrCl &lt;30</td><td>安全な正文</td></tr></table>\n\n注）原文の注記。',
  references: [
    {
      kind: "section",
      target_section_code: "2.12",
      target_url: "https://example.invalid/reference#2.12",
    },
  ],
  url: "https://example.invalid/package-insert",
  retrieved_by: ["logic", "jev", "keyword"],
};
export const visualJev = {
  model: "固定Jev",
  request_id: "visual-request",
  usage: { input_tokens: 12, output_tokens: 3 },
  answers: {
    intent: {
      choice: "warnings",
      confidence: 0.5,
      probabilities: {
        warnings: 1,
        contraindications: 0.5,
        dosage: 0,
        interactions: 0.3,
        adverse: 0.2,
        unknown_a: 0.1,
        unknown_b: 0.05,
        unknown_c: 0.02,
        unknown_d: 0.01,
      },
    },
  },
  qualifying_intents: ["warnings", "interactions"],
};
export const visualImport = {
  document_id: "visual-document",
  source_sha256: "a".repeat(64),
  status: "registered",
  reused: false,
  validation_status: "warning",
  section_count: 40,
  search_unit_count: 40,
  products: [{ yj_code: "3339003F5020", brand_name: "テスト医薬品A" }],
  revisions: [{ source_label: "今回", year_month: "2026-10", version: "1" }],
  warnings: [{ code: "missing_figure", reference: "fig05.gif" }],
  search_index_updated: true,
  generation_id: "visual-gen",
  registration_sequence: 1,
  active_yj_codes: ["3339003F5020"],
  replaced_yj_codes: [],
  deleted_version_ids: [],
  cleanup_pending: [],
  artifacts_deleted: false,
};
