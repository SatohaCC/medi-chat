import assert from "node:assert/strict";
import test from "node:test";
import { extractHighlightWords } from "./highlightWords.ts";

test("extractHighlightWords extracts whitespace-separated words", () => {
  const result = extractHighlightWords("ワルファリン 納豆 併用");
  assert.deepEqual(result, ["ワルファリン", "納豆", "併用"]);
});

test("extractHighlightWords handles full-width spaces and Japanese punctuation", () => {
  const result = extractHighlightWords("ワルファリン　納豆、併用禁忌。注意！");
  assert.deepEqual(result, ["ワルファリン", "併用禁忌", "納豆", "注意"]);
});

test("extractHighlightWords tokenizes ordinary Japanese chat sentences without spaces", () => {
  const result = extractHighlightWords("ワルファリンと納豆を併用しても大丈夫ですか？");
  assert.deepEqual(result, ["ワルファリン", "納豆", "併用"]);
});

test("extractHighlightWords sorts overlapping words longest-first", () => {
  const result = extractHighlightWords("腎機能 腎機能障害");
  assert.deepEqual(result, ["腎機能障害", "腎機能"]);
});

test("extractHighlightWords strips @ and ＠ token prefixes and extracts base medicine names", () => {
  const result = extractHighlightWords("@イグザレルト錠15mg ＠クラリス錠200mg 併用注意");
  assert.ok(result.includes("イグザレルト錠15mg"));
  assert.ok(result.includes("イグザレルト"));
  assert.ok(result.includes("クラリス錠200mg"));
  assert.ok(result.includes("クラリス"));
  assert.ok(result.includes("併用注意"));
  // Longest first check
  const idxFull = result.indexOf("イグザレルト錠15mg");
  const idxBase = result.indexOf("イグザレルト");
  assert.ok(idxFull < idxBase, "full name must precede base name");
});

test("extractHighlightWords filters single-character words and duplicates", () => {
  const result = extractHighlightWords("胃 腸 腎機能 腎機能 肝機能");
  assert.deepEqual(result, ["腎機能", "肝機能"]);
});

test("extractHighlightWords handles null, undefined, empty string", () => {
  assert.deepEqual(extractHighlightWords(null), []);
  assert.deepEqual(extractHighlightWords(undefined), []);
  assert.deepEqual(extractHighlightWords(""), []);
  assert.deepEqual(extractHighlightWords("   "), []);
});

test("medicine names and dosage fragments are excluded while clinical terms remain", () => {
  const result = extractHighlightWords(
    "イグザレルト錠２．５ｍｇとリバーロキサバンの併用禁忌・出血について教えてください",
    ["イグザレルト錠2.5mg", "リバーロキサバン"],
  );
  assert.deepEqual(result, ["併用禁忌", "出血"]);
});

test("base medicine names are excluded even when the query omits the dosage form", () => {
  assert.deepEqual(
    extractHighlightWords("@イグザレルトと納豆の併用注意", ["イグザレルト錠15mg"]),
    ["併用注意", "納豆"],
  );
});
