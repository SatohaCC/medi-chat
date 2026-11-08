import assert from "node:assert/strict";
import test from "node:test";
import { PromptDocument } from "../../../shared/component/TokenPromptInput/PromptDocument.ts";
import { buildPayloadContent, extractMentionsFromSegments } from "./promptSnapshot.ts";

test("input snapshots preserve text, URLs and custom tokens across restore and removal", () => {
  const segments = [
    { type: "text", text: "確認 " },
    {
      type: "token",
      text: "テスト対象",
      value: {
        type: "custom",
        anchor: "@",
        valueType: "medicine",
        data: { yj_code: "test-code", name: "テスト対象" },
      },
    },
    { type: "text", text: " " },
    {
      type: "token",
      text: "example",
      value: { type: "url", url: "https://example.com" },
    },
  ];
  const snapshot = new PromptDocument(segments);
  const restored = new PromptDocument(snapshot.segments);
  assert.equal(buildPayloadContent(restored), "確認 @テスト対象 https://example.com");
  assert.deepEqual(extractMentionsFromSegments(restored.segments), [
    { yj_code: "test-code", name: "テスト対象" },
  ]);
  segments[0].text = "changed";
  assert.equal(snapshot.segments[0].text, "確認 ");
  const removed = new PromptDocument(
    restored.segments.filter((segment) => segment.value?.type !== "custom"),
  );
  assert.deepEqual(extractMentionsFromSegments(removed.segments), []);
  assert.equal(buildPayloadContent(removed), "確認  https://example.com");
});
