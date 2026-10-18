import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { loadTestComponent } from "../../../scripts/load-test-component.mjs";

const { extractMedicineGroups, extractSectionGroups, SourceEvidenceSectionFilters } =
  await loadTestComponent(
    fileURLToPath(new URL("./SourceEvidenceSectionFilters.tsx", import.meta.url)),
  );

test("extractMedicineGroups counts unique medicines preserving appearance order", () => {
  const sources = [
    { product_name: "イグザレルト錠2.5mg", section: { code: "10", title: "相互作用" } },
    { product_name: "メトグルコ錠500mg", section: { code: "10", title: "相互作用" } },
    { product_name: "イグザレルト錠2.5mg", section: { code: "16", title: "薬物動態" } },
    { product_name: "メトグルコ錠500mg", section: { code: "16", title: "薬物動態" } },
  ];

  const groups = extractMedicineGroups(sources);
  assert.equal(groups.length, 2);
  assert.deepEqual(groups[0], { name: "イグザレルト錠2.5mg", count: 2 });
  assert.deepEqual(groups[1], { name: "メトグルコ錠500mg", count: 2 });
});

test("extractSectionGroups counts unique sections preserving appearance order", () => {
  const sources = [
    { product_name: "イグザレルト錠2.5mg", section: { code: "10", title: "相互作用" } },
    { product_name: "メトグルコ錠500mg", section: { code: "10", title: "相互作用" } },
    { product_name: "イグザレルト錠2.5mg", section: { code: "16", title: "薬物動態" } },
  ];

  const groups = extractSectionGroups(sources);
  assert.equal(groups.length, 2);
  assert.deepEqual(groups[0], { code: "10", title: "相互作用", count: 2 });
  assert.deepEqual(groups[1], { code: "16", title: "薬物動態", count: 1 });
});

test("SourceEvidenceSectionFilters renders both 医薬品別 and セクション別 filter rows when multiple items exist", () => {
  const sectionGroups = [
    { code: "10", title: "相互作用", count: 2 },
    { code: "16", title: "薬物動態", count: 2 },
  ];
  const medicineGroups = [
    { name: "イグザレルト錠2.5mg", count: 2 },
    { name: "メトグルコ錠500mg", count: 2 },
  ];

  const html = renderToStaticMarkup(
    createElement(SourceEvidenceSectionFilters, {
      sectionGroups,
      medicineGroups,
      totalCount: 4,
      selectedSection: "all",
      selectedMedicine: "all",
      onSelectSection: () => {},
      onSelectMedicine: () => {},
    }),
  );

  assert.match(html, /医薬品別:/);
  assert.match(html, /イグザレルト錠2\.5mg/);
  assert.match(html, /メトグルコ錠500mg/);
  assert.match(html, /セクション別:/);
  assert.match(html, /\[10\] 相互作用/);
  assert.match(html, /\[16\] 薬物動態/);
});

test("SourceEvidenceSectionFilters renders only section filters when there is only 1 medicine", () => {
  const sectionGroups = [
    { code: "10", title: "相互作用", count: 2 },
    { code: "16", title: "薬物動態", count: 1 },
  ];
  const medicineGroups = [{ name: "イグザレルト錠2.5mg", count: 3 }];

  const html = renderToStaticMarkup(
    createElement(SourceEvidenceSectionFilters, {
      sectionGroups,
      medicineGroups,
      totalCount: 3,
      selectedSection: "all",
      selectedMedicine: "all",
      onSelectSection: () => {},
      onSelectMedicine: () => {},
    }),
  );

  assert.doesNotMatch(html, /医薬品別:/);
  assert.match(html, /セクション別:/);
});
