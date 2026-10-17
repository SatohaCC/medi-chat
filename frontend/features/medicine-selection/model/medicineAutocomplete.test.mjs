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
