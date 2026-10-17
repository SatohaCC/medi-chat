import { strict as assert } from "node:assert";
import { test } from "node:test";
import { romajiToHiragana, searchMedicines } from "./medicineAutocomplete.ts";

const sampleEntries = [
  {
    n: "カロナール錠200",
    k: "",
    h: "",
    y: "1141007F1063",
    g: "アセトアミノフェン錠",
    c: "他",
  },
  {
    n: "メトグルコ錠250mg",
    k: "",
    h: "",
    y: "3962002F2027",
    g: "メトホルミン塩酸塩",
    c: "他",
  },
  {
    n: "イグザレルト錠2.5mg",
    k: "イグザレルトジョウ2.5mg",
    h: "いぐざれるとじょう2.5mg",
    y: "3339003F5020",
    g: "リバーロキサバン",
    c: "他",
  },
];

test("searchMedicines matches entries with empty k/h readings across Hiragana, Katakana, and Romaji", () => {
  for (const query of ["カロナ", "かろな", "karona", "あせと", "aseto"]) {
    const results = searchMedicines(query, sampleEntries);
    assert.equal(results[0]?.n, "カロナール錠200", `Failed for query: ${query}`);
  }

  for (const query of ["メトグ", "めとぐ", "metogu", "めとほ", "metoho"]) {
    const results = searchMedicines(query, sampleEntries);
    assert.equal(results[0]?.n, "メトグルコ錠250mg", `Failed for query: ${query}`);
  }
});

test("romajiToHiragana converts de, ji, and fe accurately", () => {
  assert.equal(romajiToHiragana("medokisomiru"), "めどきそみる");
  assert.equal(romajiToHiragana("jioru"), "じおる");
  assert.equal(romajiToHiragana("asetoaminofen"), "あせとあみのふぇん");
});

test("searchMedicines filters out entries without valid YJ code", () => {
  const mixedEntries = [
    ...sampleEntries,
    {
      n: "薬剤料減点（合算薬剤料上限超）",
      k: "ヤクザイリヨウゲンテン",
      h: "やくざいりようげんてん",
      y: "",
      g: "",
      c: "歯科",
    },
    {
      n: "包括点数の治験減点分",
      k: "",
      h: "",
      y: "   ",
      g: "",
      c: "歯科",
    },
  ];

  const results = searchMedicines("薬剤料", mixedEntries);
  assert.equal(results.length, 0);

  const results2 = searchMedicines("包括点数", mixedEntries);
  assert.equal(results2.length, 0);
});
