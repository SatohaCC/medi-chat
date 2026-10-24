const A = "a871f25a-1eb7-4c5e-8c6e-4511dce60280";
import assert from "node:assert/strict";
import { test } from "node:test";
import { parseModelOption } from "../model/chat.ts";
import { connectChatWebSocket, isWsServerMessage } from "./chatWebSocket.ts";

function setup(t, handlers = {}) {
  const originalWebSocket = globalThis.WebSocket;
  const sockets = [];
  const timers = new Map();
  const statuses = [];
  const messages = [];
  const connections = [];
  let timerId = 0;
  let now = 0;
  const listeners = new Set();
  const visibility = {
    hidden: false,
    addEventListener: (_type, callback) => listeners.add(callback),
    removeEventListener: (_type, callback) => listeners.delete(callback),
  };
  t.mock.method(Date, "now", () => now);

  class FakeWebSocket {
    static OPEN = 1;
    readyState = 0;
    sent = [];
    closeCalls = 0;

    constructor(url) {
      this.url = url;
      sockets.push(this);
    }

    open() {
      this.readyState = FakeWebSocket.OPEN;
      this.onopen?.({});
    }

    receive(data) {
      this.onmessage?.({ data });
    }

    close() {
      this.closeCalls += 1;
      this.readyState = 3;
      this.onclose?.({});
    }

    send(data) {
      this.sent.push(data);
    }
  }

  globalThis.WebSocket = FakeWebSocket;
  t.mock.method(globalThis, "setTimeout", (callback, delay) => {
    const id = ++timerId;
    timers.set(id, { callback, delay, due: now + delay });
    return id;
  });
  t.mock.method(globalThis, "clearTimeout", (id) => timers.delete(id));
  t.mock.method(Math, "random", () => 0.5);
  t.after(() => {
    for (const connection of connections) connection.disconnect();
    globalThis.WebSocket = originalWebSocket;
  });

  function start() {
    const connection = connectChatWebSocket("ws://localhost/api/ws", {
      onStatusChange: (status) => statuses.push(status),
      onMessage: (message) => messages.push(message),
      visibility,
      ...handlers,
    });
    connections.push(connection);
    return connection;
  }

  return {
    connection: start(),
    visibility,
    listeners,
    hide(hidden) {
      visibility.hidden = hidden;
      for (const callback of listeners) callback();
    },
    advance(ms) {
      const end = now + ms;
      while (true) {
        const next = [...timers]
          .filter(([, timer]) => timer.due <= end)
          .sort((a, b) => a[1].due - b[1].due)[0];
        if (!next) break;
        now = next[1].due;
        timers.delete(next[0]);
        next[1].callback();
      }
      now = end;
    },
    sockets,
    timers,
    statuses,
    messages,
    start,
    reconnect() {
      assert.equal(timers.size, 1);
      const [id, timer] = timers.entries().next().value;
      timers.delete(id);
      timer.callback();
      return sockets.at(-1);
    },
  };
}

for (const code of [4001, 1008]) {
  test(`authentication close ${code} reports expiry before clearing active state`, (t) => {
    let active = true;
    let interrupted = false;
    const { sockets } = setup(t, {
      onAuthenticationExpired: () => {
        interrupted = active;
      },
      onStatusChange: (status) => {
        if (status === "disconnected") active = false;
      },
    });
    sockets[0].open();
    sockets[0].onclose({ code });
    assert.equal(interrupted, true);
    assert.equal(active, false);
  });
}

test("TC-01: 接続状態を通知し、接続後に送受信できる", (t) => {
  const { connection, sockets, statuses, messages } = setup(t);
  const socket = sockets[0];
  assert.equal(socket.url, "ws://localhost/api/ws");
  assert.deepEqual(statuses, ["connecting"]);

  socket.open();
  const request = JSON.stringify({ type: "message", messages: [] });
  assert.equal(connection.send(request), "sent");
  socket.receive(JSON.stringify({ request_id: A, type: "text_delta", content: "回答" }));

  assert.deepEqual(statuses, ["connecting", "connected"]);
  assert.deepEqual(socket.sent, [request]);
  assert.deepEqual(messages, [{ request_id: A, type: "text_delta", content: "回答" }]);
});

test("TC-02: 接続前と切断中は送信しない", (t) => {
  const { connection, sockets, statuses } = setup(t);
  assert.equal(connection.send("送信前"), "not_open");

  sockets[0].open();
  sockets[0].close();
  assert.equal(connection.send("切断後"), "not_open");

  assert.deepEqual(sockets[0].sent, []);
  assert.deepEqual(statuses, ["connecting", "connected", "disconnected"]);
});

test("TC-03: 不正な JSON を無視し、次のメッセージを受信する", (t) => {
  const { sockets, messages } = setup(t);
  const logError = t.mock.method(console, "error", () => {});
  sockets[0].open();

  sockets[0].receive("{");
  sockets[0].receive(JSON.stringify({ request_id: A, type: "text_done" }));

  assert.equal(logError.mock.callCount(), 1);
  assert.deepEqual(messages, [{ request_id: A, type: "text_done" }]);
});

test("TC-04: 再接続は待ち時間を増やし、接続成功でリセットする", (t) => {
  const { sockets, timers, reconnect } = setup(t);
  let socket = sockets[0];

  for (const expectedDelay of [1500, 2500, 4500, 5500, 5500]) {
    socket.close();
    assert.equal(timers.values().next().value.delay, expectedDelay);
    socket = reconnect();
  }

  socket.open();
  socket.close();
  assert.equal(timers.values().next().value.delay, 1500);
});

test("TC-05: 終了した接続の遅延イベントは新しい接続に影響しない", (t) => {
  const { connection, sockets, statuses, messages, timers, start } = setup(t);
  const oldSocket = sockets[0];
  oldSocket.open();

  connection.disconnect();
  connection.disconnect();
  const nextConnection = start();
  const nextSocket = sockets[1];
  nextSocket.open();
  const currentStatuses = [...statuses];

  oldSocket.onopen({});
  oldSocket.receive(
    JSON.stringify({ request_id: A, type: "text_delta", content: "古い回答" }),
  );
  oldSocket.onclose({});
  oldSocket.onerror({});

  assert.deepEqual(statuses, currentStatuses);
  assert.deepEqual(messages, []);
  assert.equal(timers.size, 1);
  assert.equal(oldSocket.closeCalls, 1);
  assert.equal(connection.send("古い接続"), "not_open");
  assert.equal(nextConnection.send("新しい接続"), "sent");
  assert.deepEqual(nextSocket.sent, ["新しい接続"]);
});

test("TC-06: 終了時に待機中の再接続を取り消す", (t) => {
  const { connection, sockets, statuses, timers } = setup(t);
  sockets[0].close();
  const pendingReconnect = timers.values().next().value.callback;
  const currentStatuses = [...statuses];

  connection.disconnect();
  assert.equal(timers.size, 0);
  pendingReconnect();

  assert.equal(sockets.length, 1);
  assert.deepEqual(statuses, currentStatuses);
});

test("TC-07: 通信エラーで切断し、重複せず再接続する", (t) => {
  const { sockets, statuses, reconnect } = setup(t);
  sockets[0].open();

  sockets[0].onerror({});
  sockets[0].onclose({});
  assert.equal(sockets[0].closeCalls, 1);
  assert.equal(statuses.at(-1), "disconnected");

  const socket = reconnect();
  socket.open();
  assert.equal(sockets.length, 2);
  assert.equal(statuses.at(-1), "connected");
});

test("TC-WS-01: 不正な形式の WebSocket メッセージを受信した際に安全に無視・スキップする", (t) => {
  const { connection: _connection, sockets, messages } = setup(t);
  sockets[0].open();

  // 1. type なしのオブジェクト
  sockets[0].receive(JSON.stringify({}));
  // 2. null
  sockets[0].receive("null");
  // 3. 文字列プリミティブ
  sockets[0].receive(JSON.stringify("just a string"));
  // 4. 未知の type
  sockets[0].receive(JSON.stringify({ type: "unknown_future_message" }));
  // 5. 正常なメッセージ
  sockets[0].receive(
    JSON.stringify({ request_id: A, type: "text_delta", content: "hello" }),
  );

  assert.equal(messages.length, 1);
  assert.deepEqual(messages[0], { request_id: A, type: "text_delta", content: "hello" });
});

test("TC-WS-02: 有効な WsServerMessage 型が isWsServerMessage で正常に判定される", () => {
  assert.equal(
    isWsServerMessage({ request_id: A, type: "text_delta", content: "chunk" }),
    true,
  );
  assert.equal(isWsServerMessage({ request_id: A, type: "text_done" }), true);
  assert.equal(
    isWsServerMessage({ request_id: A, type: "notices", notices: ["notice1"] }),
    true,
  );
  assert.equal(isWsServerMessage({ request_id: A, type: "sources", sources: [] }), true);
  assert.equal(
    isWsServerMessage({ request_id: A, type: "retrieval_status", stage: "complete" }),
    true,
  );
  assert.equal(
    isWsServerMessage({ request_id: A, type: "jev_response", data: {} }),
    true,
  );
  assert.equal(
    isWsServerMessage({ request_id: A, type: "error", content: "fail" }),
    true,
  );

  // 異常系
  assert.equal(isWsServerMessage(null), false);
  assert.equal(isWsServerMessage(undefined), false);
  assert.equal(isWsServerMessage("string"), false);
  assert.equal(isWsServerMessage(123), false);
  assert.equal(isWsServerMessage({}), false);
  assert.equal(isWsServerMessage({ type: "unknown" }), false);
});

test("TC-WS-03: ChatWebSocketConnection の Symbol.dispose による明示的リソース破棄", (t) => {
  const { connection, sockets, timers } = setup(t);
  sockets[0].close();
  assert.equal(timers.size, 1);

  if (
    typeof Symbol.dispose === "symbol" &&
    typeof connection[Symbol.dispose] === "function"
  ) {
    connection[Symbol.dispose]();
    assert.equal(timers.size, 0);
    assert.equal(connection.send("テスト"), "not_open");
  } else {
    assert.fail("Symbol.dispose が connection に実装されていません");
  }
});

test("TC-WS-04: ChatWebSocketConnection.send はオブジェクトを自動で JSON シリアライズして送信する", (t) => {
  const { connection, sockets } = setup(t);
  sockets[0].open();

  const clientMessage = {
    type: "message",
    provider: "openai",
    model: "gpt-6-luna",
    product_yj_codes: ["3339003F5020"],
    messages: [{ role: "user", content: "こんにちは" }],
  };

  const ok = connection.send(clientMessage);
  assert.equal(ok, "sent");
  assert.equal(sockets[0].sent.length, 1);
  assert.equal(sockets[0].sent[0], JSON.stringify(clientMessage));
});

test("TC-WS-05: parseModelOption はモデル指定文字列を provider と model に安全に分解する", () => {
  assert.deepEqual(parseModelOption("openai:gpt-6-luna"), {
    provider: "openai",
    model: "gpt-6-luna",
  });
  assert.deepEqual(parseModelOption("google:gemini-3.8-flash:experimental"), {
    provider: "google",
    model: "gemini-3.8-flash:experimental",
  });
  assert.deepEqual(parseModelOption("invalid-format"), {
    provider: "",
    model: "invalid-format",
  });
});

test("WR-005 strict business IDs and control union", () => {
  for (const id of [undefined, "", "bad", 3, "a871f25a-1eb7-1c5e-8c6e-4511dce60280"]) {
    assert.equal(isWsServerMessage({ type: "text_done", request_id: id }), false);
  }
  assert.equal(isWsServerMessage({ type: "aborted", request_id: A }), true);
  assert.equal(isWsServerMessage({ type: "pong", ping_id: A }), true);
  assert.equal(isWsServerMessage({ type: "pong", ping_id: "bad" }), false);
  assert.equal(
    isWsServerMessage({
      type: "control_error",
      request_id: A,
      code: "busy",
      content: "busy",
    }),
    true,
  );
  assert.equal(
    isWsServerMessage({
      type: "control_error",
      request_id: A,
      code: "wrong",
      content: "busy",
    }),
    false,
  );
  assert.equal(
    isWsServerMessage({
      type: "connection_error",
      code: "invalid_payload",
      content: "invalid",
    }),
    true,
  );
});

test("WR-026 WR-027 idle and pong deadline boundaries", (t) => {
  const env = setup(t);
  const socket = env.sockets[0];
  socket.open();
  env.advance(29999);
  assert.equal(socket.sent.length, 0);
  env.advance(1);
  const ping = JSON.parse(socket.sent[0]);
  assert.equal(ping.type, "ping");
  assert.match(ping.ping_id, /^[0-9a-f-]{14}4[0-9a-f-]+$/i);
  env.advance(4999);
  assert.equal(env.statuses.at(-1), "connected");
  socket.receive(JSON.stringify({ type: "pong", ping_id: ping.ping_id }));
  env.advance(1);
  assert.equal(env.statuses.at(-1), "connected");
  env.advance(29999);
  assert.equal(socket.sent.length, 2);
  env.advance(5000);
  assert.equal(env.statuses.at(-1), "disconnected");
  assert.equal(env.timers.size, 1);
});

test("WR-028 WR-029 valid traffic resets idle but cannot satisfy outstanding ping", (t) => {
  const env = setup(t);
  const socket = env.sockets[0];
  socket.open();
  env.advance(20000);
  socket.receive(
    JSON.stringify({ type: "text_delta", request_id: A, content: "テスト" }),
  );
  env.advance(29999);
  assert.equal(socket.sent.length, 0);
  env.advance(1);
  env.advance(4000);
  socket.receive(JSON.stringify({ type: "text_done", request_id: A }));
  socket.receive(
    JSON.stringify({ type: "pong", ping_id: "b871f25a-1eb7-4c5e-8c6e-4511dce60280" }),
  );
  socket.receive("{");
  env.advance(1000);
  assert.equal(env.statuses.at(-1), "disconnected");
});

test("WR-030 half-open timeout error close invalidates only once without onclose", (t) => {
  const env = setup(t);
  const old = env.sockets[0];
  old.open();
  old.close = () => {
    old.closeCalls++;
    old.readyState = 3;
  };
  env.advance(35000);
  old.onerror({});
  old.onclose({});
  assert.equal(env.statuses.filter((s) => s === "disconnected").length, 1);
  assert.equal(env.timers.size, 1);
  env.advance(1500);
  const current = env.sockets[1];
  current.open();
  old.onclose({});
  old.onerror({});
  assert.equal(current.closeCalls, 0);
});

test("WR-031 WR-032 WR-033 visibility renews probe, gates business and disposes subscriptions", (t) => {
  const env = setup(t);
  const socket = env.sockets[0];
  socket.open();
  env.advance(30000);
  const old = JSON.parse(socket.sent[0]);
  const deadline = [...env.timers.values()][0].callback;
  env.hide(true);
  assert.equal(env.timers.size, 0);
  env.advance(60000);
  env.hide(false);
  const ping = JSON.parse(socket.sent[1]);
  assert.notEqual(ping.ping_id, old.ping_id);
  assert.equal(env.connection.send("business"), "not_open");
  deadline();
  assert.equal(env.statuses.at(-1), "connected");
  socket.receive(JSON.stringify({ type: "pong", ping_id: old.ping_id }));
  assert.equal(env.connection.send("business"), "not_open");
  socket.receive(JSON.stringify({ type: "pong", ping_id: ping.ping_id }));
  assert.equal(env.connection.send("business"), "sent");
  env.connection.disconnect();
  assert.equal(env.listeners.size, 0);
  assert.equal(env.timers.size, 0);
  env.advance(60000);
});

test("WR-047 send attempt exceptions are uncertain and never retried", (t) => {
  const env = setup(t);
  env.sockets[0].open();
  env.sockets[0].send = () => {
    throw new Error("test send");
  };
  assert.equal(env.connection.send("business"), "uncertain");
  assert.equal(env.statuses.at(-1), "disconnected");
  env.advance(1500);
  env.sockets[1].open();
  assert.deepEqual(env.sockets[1].sent, []);
});
