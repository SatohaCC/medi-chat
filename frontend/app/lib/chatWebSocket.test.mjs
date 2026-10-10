import assert from "node:assert/strict";
import { test } from "node:test";
import { connectChatWebSocket } from "./chatWebSocket.ts";

function setup(t) {
  const originalWebSocket = globalThis.WebSocket;
  const sockets = [];
  const timers = new Map();
  const statuses = [];
  const messages = [];
  const connections = [];
  let timerId = 0;

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
    timers.set(id, { callback, delay });
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
    });
    connections.push(connection);
    return connection;
  }

  return {
    connection: start(),
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

test("TC-01: 接続状態を通知し、接続後に送受信できる", (t) => {
  const { connection, sockets, statuses, messages } = setup(t);
  const socket = sockets[0];
  assert.equal(socket.url, "ws://localhost/api/ws");
  assert.deepEqual(statuses, ["connecting"]);

  socket.open();
  const request = JSON.stringify({ type: "message", messages: [] });
  assert.equal(connection.send(request), true);
  socket.receive(JSON.stringify({ type: "text_delta", content: "回答" }));

  assert.deepEqual(statuses, ["connecting", "connected"]);
  assert.deepEqual(socket.sent, [request]);
  assert.deepEqual(messages, [{ type: "text_delta", content: "回答" }]);
});

test("TC-02: 接続前と切断中は送信しない", (t) => {
  const { connection, sockets, statuses } = setup(t);
  assert.equal(connection.send("送信前"), false);

  sockets[0].open();
  sockets[0].close();
  assert.equal(connection.send("切断後"), false);

  assert.deepEqual(sockets[0].sent, []);
  assert.deepEqual(statuses, ["connecting", "connected", "disconnected"]);
});

test("TC-03: 不正な JSON を無視し、次のメッセージを受信する", (t) => {
  const { sockets, messages } = setup(t);
  const logError = t.mock.method(console, "error", () => {});
  sockets[0].open();

  sockets[0].receive("{");
  sockets[0].receive(JSON.stringify({ type: "text_done" }));

  assert.equal(logError.mock.callCount(), 1);
  assert.deepEqual(messages, [{ type: "text_done" }]);
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
  oldSocket.receive(JSON.stringify({ type: "text_delta", content: "古い回答" }));
  oldSocket.onclose({});
  oldSocket.onerror({});

  assert.deepEqual(statuses, currentStatuses);
  assert.deepEqual(messages, []);
  assert.equal(timers.size, 0);
  assert.equal(oldSocket.closeCalls, 1);
  assert.equal(connection.send("古い接続"), false);
  assert.equal(nextConnection.send("新しい接続"), true);
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
