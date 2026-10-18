import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  buildPayloadContent,
  computeTargetMedicines,
  extractMentionsFromSegments,
  resolvePostSendState,
} from "./promptSnapshot.ts";

describe("promptSnapshot model", () => {
  const medA = { yj_code: "1111001", name: "イグザレルト錠15mg" };
  const medB = { yj_code: "2222002", name: "ロキソニン錠60mg" };
  const medD = { yj_code: "3333003", name: "ムコスタ錠100mg" };

  // TC-M01: 複数トークンを含む PromptFieldValue のシリアライズ
  it("TC-M01: serializes prompt with multiple tokens preserving text order, tokens, and newlines", () => {
    const segments = [
      { type: "text", text: "処方を " },
      {
        type: "token",
        text: medA.name,
        value: { type: "custom", anchor: "@", valueType: "medicine", data: medA },
      },
      { type: "text", text: " から\n" },
      {
        type: "token",
        text: medB.name,
        value: { type: "custom", anchor: "@", valueType: "medicine", data: medB },
      },
      { type: "text", text: " へ変更してもよいですか？" },
    ];

    const content = buildPayloadContent(segments);
    assert.equal(
      content,
      "処方を @イグザレルト錠15mg から\n@ロキソニン錠60mg へ変更してもよいですか？",
    );

    const mentions = extractMentionsFromSegments(segments);
    assert.deepEqual(mentions, [medA, medB]);
  });

  // TC-M02: 同一薬品トークンが 2 回現れる場合のシリアライズと重複排除
  it("TC-M02: preserves both tokens in serialized text but deduplicates extracted YJ codes", () => {
    const segments = [
      { type: "text", text: "朝に " },
      {
        type: "token",
        text: medB.name,
        value: { type: "custom", anchor: "@", valueType: "medicine", data: medB },
      },
      { type: "text", text: "、夕にも " },
      {
        type: "token",
        text: medB.name,
        value: { type: "custom", anchor: "@", valueType: "medicine", data: medB },
      },
      { type: "text", text: " を服用" },
    ];

    const content = buildPayloadContent(segments);
    assert.equal(content, "朝に @ロキソニン錠60mg、夕にも @ロキソニン錠60mg を服用");

    const mentions = extractMentionsFromSegments(segments);
    assert.deepEqual(mentions, [medB]);
  });

  // TC-M03: 状態遷移マトリクス 行1〜7の完全一致
  describe("TC-M03: state transition matrix (rows 1-7)", () => {
    it("Row 1: B=[A], C=[], M=[B] -> T=[A, B], postSend C=[B]", () => {
      const state = computeTargetMedicines({
        baseline: [medA],
        persistentAdditional: [],
        mentions: [medB],
      });
      assert.equal(state.canSend, true);
      assert.deepEqual(state.target, [medA, medB]);
      assert.deepEqual(state.additional, [medB]);

      const post = resolvePostSendState(state);
      assert.deepEqual(post.baseline, [medA]);
      assert.deepEqual(post.persistentAdditional, [medB]);
    });

    it("Row 2: B=[A], C=[B], M=[] -> T=[A, B], postSend C=[B]", () => {
      const state = computeTargetMedicines({
        baseline: [medA],
        persistentAdditional: [medB],
        mentions: [],
      });
      assert.equal(state.canSend, true);
      assert.deepEqual(state.target, [medA, medB]);
      assert.deepEqual(state.additional, [medB]);

      const post = resolvePostSendState(state);
      assert.deepEqual(post.baseline, [medA]);
      assert.deepEqual(post.persistentAdditional, [medB]);
    });

    it("Row 3: B=[A], C=[B], M=[D] -> T=[A, D], postSend C=[D]", () => {
      const state = computeTargetMedicines({
        baseline: [medA],
        persistentAdditional: [medB],
        mentions: [medD],
      });
      assert.equal(state.canSend, true);
      assert.deepEqual(state.target, [medA, medD]);
      assert.deepEqual(state.additional, [medD]);

      const post = resolvePostSendState(state);
      assert.deepEqual(post.baseline, [medA]);
      assert.deepEqual(post.persistentAdditional, [medD]);
    });

    it("Row 4: B=[A], C=[], M=[A, A] -> T=[A], postSend C=[]", () => {
      const state = computeTargetMedicines({
        baseline: [medA],
        persistentAdditional: [],
        mentions: [medA, medA],
      });
      assert.equal(state.canSend, true);
      assert.deepEqual(state.target, [medA]);
      assert.deepEqual(state.additional, []);

      const post = resolvePostSendState(state);
      assert.deepEqual(post.baseline, [medA]);
      assert.deepEqual(post.persistentAdditional, []);
    });

    it("Row 5: B=[], C=[], M=[B] -> T=[B], postSend C=[B]", () => {
      const state = computeTargetMedicines({
        baseline: [],
        persistentAdditional: [],
        mentions: [medB],
      });
      assert.equal(state.canSend, true);
      assert.deepEqual(state.target, [medB]);
      assert.deepEqual(state.additional, [medB]);

      const post = resolvePostSendState(state);
      assert.deepEqual(post.baseline, []);
      assert.deepEqual(post.persistentAdditional, [medB]);
    });

    it("Row 6: B=[], C=[B], M=[] -> T=[B], postSend C=[B]", () => {
      const state = computeTargetMedicines({
        baseline: [],
        persistentAdditional: [medB],
        mentions: [],
      });
      assert.equal(state.canSend, true);
      assert.deepEqual(state.target, [medB]);
      assert.deepEqual(state.additional, [medB]);

      const post = resolvePostSendState(state);
      assert.deepEqual(post.baseline, []);
      assert.deepEqual(post.persistentAdditional, [medB]);
    });

    it("Row 7: B=[], C=[], M=[] -> canSend=false", () => {
      const state = computeTargetMedicines({
        baseline: [],
        persistentAdditional: [],
        mentions: [],
      });
      assert.equal(state.canSend, false);
      assert.deepEqual(state.target, []);
      assert.deepEqual(state.additional, []);
    });
  });

  // TC-M04: ベース薬 A を本文でメンションした場合、追加薬は 0 件
  it("TC-M04: mentioning baseline drug A results in target [A] and 0 additional drugs", () => {
    const state = computeTargetMedicines({
      baseline: [medA],
      persistentAdditional: [],
      mentions: [medA],
    });
    assert.deepEqual(state.target, [medA]);
    assert.deepEqual(state.additional, []);
  });

  // TC-M05: トークンを挿入後に全削除した場合、古い C が復活せず T=B に戻る
  it("TC-M05: when token is edited and deleted, discarded C does not resurrect and T=B safely", () => {
    // When editing started, C was discarded: persistentAdditional becomes []
    const state = computeTargetMedicines({
      baseline: [medA],
      persistentAdditional: [], // discarded upon user editing
      mentions: [], // all deleted
    });
    assert.deepEqual(state.target, [medA]);
    assert.deepEqual(state.additional, []);
  });

  // TC-M06: プレーンテキスト貼り付けの「@ロキソニン」はトークンにならず YJ 抽出されない
  it("TC-M06: plain text '@ロキソニン' is treated as text segment and not extracted as medicine", () => {
    const segments = [{ type: "text", text: "貼り付けた @ロキソニン錠60mg の情報" }];
    const content = buildPayloadContent(segments);
    assert.equal(content, "貼り付けた @ロキソニン錠60mg の情報");

    const mentions = extractMentionsFromSegments(segments);
    assert.deepEqual(mentions, []);
  });
});

describe("mergeMedicineEntries", () => {
  // TC-D01: static dictionary is preserved and merged with active medicines
  it("TC-D01: merges static dictionary entries with active catalog items without dropping un-imported medicines", async () => {
    const { mergeMedicineEntries } = await import("./medicineEntries.ts");
    const active = [
      {
        n: "イグザレルト錠15mg (Active)",
        k: "イグザレルト",
        h: "いぐざれると",
        y: "3339003F5020",
        g: "リバーロキサバン錠",
        c: "内用",
      },
    ];
    const staticDict = [
      {
        n: "イグザレルト錠15mg",
        k: "イグザレルト",
        h: "いぐざれると",
        y: "3339003F5020",
        g: "リバーロキサバン錠",
        c: "内用",
      },
      {
        n: "ロキソニン錠60mg",
        k: "ロキソニン",
        h: "ろきそにん",
        y: "1141007F1063",
        g: "ロキソプロフェンナトリウム水和物錠",
        c: "内用",
      },
    ];

    const merged = mergeMedicineEntries(active, staticDict);
    assert.equal(merged.length, 2);
    // Active entry details override static entry for the same YJ
    const igz = merged.find((m) => m.y === "3339003F5020");
    assert.equal(igz?.n, "イグザレルト錠15mg (Active)");
    // Static-only entry is preserved
    const roki = merged.find((m) => m.y === "1141007F1063");
    assert.equal(roki?.n, "ロキソニン錠60mg");
  });

  it("TC-D02: falls back to static dictionary when active catalog is empty", async () => {
    const { mergeMedicineEntries } = await import("./medicineEntries.ts");
    const staticDict = [
      {
        n: "ロキソニン錠60mg",
        k: "ロキソニン",
        h: "ろきそにん",
        y: "1141007F1063",
        g: "ロキソプロフェンナトリウム水和物錠",
        c: "内用",
      },
    ];
    const merged = mergeMedicineEntries([], staticDict);
    assert.equal(merged.length, 1);
    assert.equal(merged[0].y, "1141007F1063");
  });
});

for (const count of [0, 1, 9, 50, 51]) {
  it(`supports up to 50 targets without dropping any selected medicine (${count})`, () => {
    const baseline = Array.from({ length: count }, (_, i) => ({
      yj_code: String(i).padStart(12, "0"),
      name: `テスト薬${i}`,
    }));
    const result = computeTargetMedicines({
      baseline,
      persistentAdditional: [],
      mentions: [],
    });
    assert.equal(result.canSend, count > 0 && count <= 50);
    assert.deepEqual(result.target, baseline);
  });
}
