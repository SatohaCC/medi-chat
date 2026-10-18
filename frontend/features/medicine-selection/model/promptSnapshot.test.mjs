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
