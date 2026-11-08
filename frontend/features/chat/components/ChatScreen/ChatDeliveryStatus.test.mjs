import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { loadTestComponent } from "../../../../scripts/load-test-component.mjs";

const { ChatDeliveryStatus } = await loadTestComponent(
  fileURLToPath(new URL("./ChatDeliveryStatus.tsx", import.meta.url)),
);
const question = {
  content: "テスト質問",
  payload: { request_id: "test-id" },
  context: { targets: [{ name: "テスト対象" }], model: "test-model" },
  reason: "cancelled",
};
const actions = {
  onCancelPending() {},
  onEdit() {},
  onKeepDraft() {},
  onReplaceDraft() {},
};
test("delivery presentation renders pending, cancellation and explicit replacement from supplied data", () => {
  const html = renderToStaticMarkup(
    createElement(ChatDeliveryStatus, {
      ...actions,
      pending: question,
      unsent: [question],
      restoreChoice: question,
    }),
  );
  for (const text of [
    "未送信の保留",
    "テスト質問",
    "テスト対象",
    "test-model",
    "取消",
    "再編集の確認",
    "現在の入力を保持",
    "元の質問に置換",
  ])
    assert.ok(html.includes(text), text);
  assert.equal(
    renderToStaticMarkup(
      createElement(ChatDeliveryStatus, {
        ...actions,
        pending: null,
        unsent: [],
        restoreChoice: null,
      }),
    ),
    "",
  );
});
