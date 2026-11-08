import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { toMedicinePickerOptions } from "./medicinePickerOptions.ts";

describe("medicinePickerOptions model", () => {
  const isoniazid = {
    n: "イソニアジド",
    k: "イソニアジド",
    h: "いそにあじど",
    y: "6222001X1013",
    g: "イソニアジド",
    c: "内用",
  };
  const iscocine = {
    n: "イスコチン原末",
    k: "イスコチンゲンマツ",
    h: "いすこちんげんまつ",
    y: "6222001X1013",
    g: "イソニアジド",
    c: "内用",
  };

  it("同一YJコードの製品でも選択肢IDが重複しない", () => {
    const options = toMedicinePickerOptions([isoniazid, iscocine]);

    assert.equal(options.length, 2);
    assert.equal(new Set(options.map((option) => option.id)).size, 2);
    assert.deepEqual(
      options.map((option) => option.label),
      ["イソニアジド", "イスコチン原末"],
    );
  });

  it("選択肢IDから選択された製品を一意に引ける", () => {
    const options = toMedicinePickerOptions([isoniazid, iscocine]);
    const selected = options.find((option) => option.id === options[1].id);

    assert.equal(selected?.entry.n, "イスコチン原末");
    assert.equal(selected?.entry.y, "6222001X1013");
  });

  it("同じ製品名の候補が並んでもIDを一意に保つ", () => {
    const options = toMedicinePickerOptions([isoniazid, { ...isoniazid }]);

    assert.equal(new Set(options.map((option) => option.id)).size, 2);
  });
});
