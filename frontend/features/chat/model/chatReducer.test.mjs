const A = "a871f25a-1eb7-4c5e-8c6e-4511dce60280";
import assert from "node:assert/strict";
import { test } from "node:test";
import { chatReducer, initialChatState } from "./chatReducer.ts";

test("chatReducer: start_message はユーザーとアシスタントのメッセージを追加しフラグを立てる", () => {
  const next = chatReducer(initialChatState, {
    type: "start_message",
    userContent: "質問内容",
    requestId: A,
  });

  assert.equal(next.activeRequest, true);
  assert.equal(next.isStreaming, true);
  assert.equal(next.messages.length, 2);
  assert.deepEqual(next.messages[0], { role: "user", content: "質問内容", requestId: A });
  assert.deepEqual(next.messages[1], { role: "assistant", content: "", requestId: A });
});

test("chatReducer: text_delta は直前のアシスタントの content に差分を追記する", () => {
  const stateWithAssistant = {
    ...initialChatState,
    activeRequest: true,
    activeRequestId: A,
    messages: [
      { role: "user", content: "質問" },
      { role: "assistant", content: "初め" },
    ],
  };

  const next = chatReducer(stateWithAssistant, {
    type: "server_message",
    message: { request_id: A, type: "text_delta", content: "の言葉" },
  });

  assert.equal(next.messages[1].content, "初めの言葉");
});

test("chatReducer: sources / retrieval_status / notices を直前のアシスタントに反映する", () => {
  const stateWithAssistant = {
    ...initialChatState,
    activeRequest: true,
    activeRequestId: A,
    messages: [
      { role: "user", content: "質問" },
      { role: "assistant", content: "回答" },
    ],
  };

  const state1 = chatReducer(stateWithAssistant, {
    type: "server_message",
    message: { request_id: A, type: "sources", sources: [{ product_name: "薬A" }] },
  });
  assert.equal(state1.messages[1].sources[0].product_name, "薬A");

  const state2 = chatReducer(state1, {
    type: "server_message",
    message: {
      request_id: A,
      type: "retrieval_status",
      stage: "complete",
      jev_response: null,
    },
  });
  assert.equal(state2.messages[1].retrievalStatus, "complete");

  const state3 = chatReducer(state2, {
    type: "server_message",
    message: { request_id: A, type: "notices", notices: ["注意文"] },
  });
  assert.deepEqual(state3.messages[1].notices, ["注意文"]);
});

test("chatReducer: text_done は isStreaming と activeRequest を解除する", () => {
  const streamingState = {
    ...initialChatState,
    activeRequestId: A,
    isStreaming: true,
    activeRequest: true,
  };

  const next = chatReducer(streamingState, {
    type: "server_message",
    message: { request_id: A, type: "text_done" },
  });

  assert.equal(next.isStreaming, false);
  assert.equal(next.activeRequest, false);
});

test("chatReducer: error はエラー内容を設定してストリーミングを解除する", () => {
  const streamingState = {
    ...initialChatState,
    activeRequestId: A,
    isStreaming: true,
    activeRequest: true,
    messages: [
      { role: "user", content: "質問" },
      { role: "assistant", content: "途中" },
    ],
  };

  const next = chatReducer(streamingState, {
    type: "server_message",
    message: { request_id: A, type: "error", content: "エラー発生" },
  });

  assert.equal(next.isStreaming, false);
  assert.equal(next.activeRequest, false);
  assert.equal(next.messages[1].content, "エラー発生");
  assert.equal(next.messages[1].isError, true);
});

test("chatReducer: status_change で disconnected になった時、進行中リクエストがあれば中断マークをつける", () => {
  const activeState = {
    ...initialChatState,
    activeRequestId: A,
    status: "connected",
    activeRequest: true,
    isStreaming: true,
    messages: [
      { role: "user", content: "質問" },
      { role: "assistant", content: "途中" },
    ],
  };

  const next = chatReducer(activeState, {
    type: "status_change",
    status: "disconnected",
  });

  assert.equal(next.status, "disconnected");
  assert.equal(next.activeRequest, false);
  assert.equal(next.isStreaming, false);
  assert.equal(next.messages[0].isInterrupted, true);
  assert.equal(next.messages[1].isInterrupted, true);
});

test("chatReducer: auth_expired は進行中リクエストを中断し、有効期限切れメッセージを付与する", () => {
  const activeState = {
    ...initialChatState,
    activeRequestId: A,
    activeRequest: true,
    isStreaming: true,
    messages: [
      { role: "user", content: "質問" },
      { role: "assistant", content: "回答の一部" },
    ],
  };

  const next = chatReducer(activeState, {
    type: "auth_expired",
  });

  assert.equal(next.activeRequest, false);
  assert.equal(next.isStreaming, false);
  assert.equal(next.messages[0].isInterrupted, true);
  assert.equal(next.messages[1].isInterrupted, true);
  assert.equal(next.messages[1].isError, true);
  assert.match(next.messages[1].content, /ログインの有効期限が切れたため/);
});

test("chatReducer: auth_expired はリクエスト進行中でなければ何もしない", () => {
  const idleState = {
    ...initialChatState,
    activeRequestId: A,
    activeRequest: false,
    messages: [],
  };

  const next = chatReducer(idleState, { type: "auth_expired" });
  assert.deepEqual(next, idleState);
});

const B = "b871f25a-1eb7-4c5e-8c6e-4511dce60280";
test("WR-006 isolates every event and ignores post-terminal delivery", () => {
  let state = chatReducer(initialChatState, {
    type: "start_message",
    userContent: "テスト質問",
    requestId: A,
  });
  const events = [
    { type: "text_delta", content: "answer" },
    { type: "sources", sources: [] },
    { type: "retrieval_status", stage: "complete" },
    { type: "jev_response", data: {} },
    { type: "notices", notices: [] },
    { type: "error", content: "error" },
    { type: "text_done" },
    { type: "aborted" },
  ];
  for (const request_id of [B, undefined, "bad"])
    for (const event of events) {
      assert.deepEqual(
        chatReducer(state, { type: "server_message", message: { ...event, request_id } }),
        state,
      );
    }
  state = chatReducer(state, {
    type: "server_message",
    message: { type: "text_delta", request_id: A, content: "テスト回答" },
  });
  assert.equal(state.messages[1].content, "テスト回答");
  state = chatReducer(state, {
    type: "server_message",
    message: { type: "text_done", request_id: A },
  });
  for (const event of events)
    assert.deepEqual(
      chatReducer(state, {
        type: "server_message",
        message: { ...event, request_id: A },
      }),
      state,
    );
});
