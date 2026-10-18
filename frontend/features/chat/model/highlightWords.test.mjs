import assert from "node:assert/strict";
import test from "node:test";
import { extractHighlightWords } from "./highlightWords.ts";

test("extractHighlightWords extracts whitespace-separated words", () => {
  const result = extractHighlightWords("ワルファリン 納豆 併用");
  assert.deepEqual(result, ["ワルファリン", "納豆", "併用"]);
});

test("extractHighlightWords handles full-width spaces and Japanese punctuation", () => {
  const result = extractHighlightWords("ワルファリン　納豆、併用禁忌。注意！");
  assert.deepEqual(result, ["ワルファリン", "納豆", "併用禁忌", "注意"]);
});

test("extractHighlightWords strips @ and ＠ token prefixes", () => {
  const result = extractHighlightWords("@イグザレルト錠15mg ＠クラリス錠200mg 併用注意");
  assert.deepEqual(result, ["イグザレルト錠15mg", "クラリス錠200mg", "併用注意"]);
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
