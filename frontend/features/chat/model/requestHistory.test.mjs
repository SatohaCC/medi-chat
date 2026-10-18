import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { loadTestComponent } from "../../../scripts/load-test-component.mjs";

const { buildRequestHistory } = await loadTestComponent(
  fileURLToPath(new URL("./requestHistory.ts", import.meta.url)),
);

test("26th and later questions retain recent complete turns within the API limit", () => {
  const history = Array.from({ length: 30 }, (_, i) => [
    { role: "user", content: `テスト質問${i}` },
    { role: "assistant", content: `テスト回答${i}` },
  ]).flat();
  const original = structuredClone(history);
  const payload = buildRequestHistory(history, "最新の質問");
  assert.equal(payload.length, 49);
  assert.deepEqual(payload[0], history[12]);
  assert.deepEqual(payload.at(-1), { role: "user", content: "最新の質問" });
  assert.deepEqual(history, original);
});

test("oversized answers and failed or interrupted turns cannot poison later requests", () => {
  const history = [
    { role: "user", content: "長い回答の質問" },
    { role: "assistant", content: "長".repeat(4001) },
    { role: "user", content: "失敗した質問" },
    { role: "assistant", content: "エラー", isError: true },
    { role: "user", content: "中断", isInterrupted: true },
    { role: "assistant", content: "途中", isInterrupted: true },
    { role: "user", content: "成功した質問" },
    { role: "assistant", content: "正確な回答" },
  ];
  assert.deepEqual(buildRequestHistory(history, "次の質問"), [
    { role: "user", content: "成功した質問" },
    { role: "assistant", content: "正確な回答" },
    { role: "user", content: "次の質問" },
  ]);
});
