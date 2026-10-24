import assert from "node:assert/strict";
import { test } from "node:test";
import { ChatRequestLifecycle } from "./chatRequestLifecycle.ts";
const A = "a871f25a-1eb7-4c5e-8c6e-4511dce60280";
const B = "b871f25a-1eb7-4c5e-8c6e-4511dce60280";
function setup() {
  const sent = [],
    starts = [],
    events = [];
  const owner = new ChatRequestLifecycle({
    send: (p) => {
      sent.push(p);
      return "sent";
    },
    start: (...s) => starts.push(s),
    event: (e) => events.push(e),
  });
  return { owner, sent, starts, events };
}
const payload = (id) => ({
  type: "message",
  request_id: id,
  provider: "openai",
  model: "gpt-6-luna",
  product_yj_codes: ["123456789012"],
  messages: [{ role: "user", content: "テスト質問" }],
});
test("WR-007 mismatched terminal cannot release synchronous reservation", () => {
  const { owner, sent, events } = setup();
  assert.equal(owner.send(payload(A), "A").ok, true);
  for (const event of [
    { type: "text_done", request_id: B },
    { type: "error", request_id: B, content: "bad" },
    { type: "control_error", request_id: A, code: "busy", content: "busy" },
    { type: "connection_error", code: "invalid_payload", content: "bad" },
  ])
    owner.receive(event);
  assert.equal(owner.send(payload(B), "B").reason, "busy");
  assert.equal(sent.length, 1);
  assert.equal(events.length, 0);
  owner.receive({ type: "text_done", request_id: A });
  assert.equal(owner.send(payload(B), "B").ok, true);
  owner.receive({ type: "text_delta", request_id: A, content: "late" });
  owner.receive({ type: "aborted", request_id: A });
  assert.equal(owner.activeId, B);
  assert.equal(events.length, 1);
});
test("WR-009 same tick only reserves one request", () => {
  const { owner, sent, starts } = setup();
  owner.send(payload(A), "A");
  assert.equal(owner.send(payload(B), "B").reason, "busy");
  assert.equal(sent.length, 1);
  assert.equal(starts.length, 1);
});

function pendingSetup(t) {
  let ready = false,
    allowed = true,
    result = "sent",
    now = 0;
  const sent = [],
    starts = [],
    updates = [],
    events = [];
  const owner = new ChatRequestLifecycle({
    send: (p) => {
      sent.push(structuredClone(p));
      return result;
    },
    ready: () => ready,
    canQueue: () => allowed,
    start: (...s) => starts.push(s),
    event: (e) => events.push(e),
    pending: (...args) => updates.push(args),
    now: () => now,
  });
  t.after(() => owner.dispose());
  return {
    owner,
    sent,
    starts,
    updates,
    events,
    setReady: (v) => (ready = v),
    setAllowed: (v) => (allowed = v),
    setResult: (v) => (result = v),
    time: (v) => (now = v),
  };
}
test("WR-035 WR-036 WR-037 WR-038 one frozen pending snapshot flushes once", (t) => {
  const env = pendingSetup(t);
  const input = payload(A);
  const context = {
    promptSegments: [{ type: "text", text: "テスト質問" }],
    targets: [{ yj_code: "123456789012", name: "テスト薬" }],
    model: "openai:gpt-6-luna",
  };
  assert.deepEqual(env.owner.send(input, "テスト質問", context), {
    ok: true,
    disposition: "queued",
    requestId: A,
  });
  assert.equal(env.owner.send(payload(B), "B").reason, "queue_full");
  assert.equal(env.sent.length, 0);
  input.provider = "gemini";
  input.model = "changed";
  input.product_yj_codes[0] = "changed";
  input.messages[0].content = "changed";
  context.promptSegments[0].text = "changed";
  assert.equal(env.owner.pending.context.promptSegments[0].text, "テスト質問");
  env.setReady(true);
  env.owner.flush();
  env.owner.flush();
  assert.equal(env.sent.length, 1);
  assert.deepEqual(env.sent[0], payload(A));
  assert.equal(env.owner.pending, null);
  assert.equal(env.owner.activeId, A);
  assert.equal(env.owner.send(payload(B), "B").reason, "busy");
});
test("WR-039 not_open retains pending until next ready", (t) => {
  const env = pendingSetup(t);
  env.owner.send(payload(A), "A");
  env.setReady(true);
  env.setResult("not_open");
  env.owner.flush();
  assert.equal(env.owner.pending.payload.request_id, A);
  env.setResult("sent");
  env.owner.flush();
  env.owner.flush();
  assert.equal(env.sent.length, 2);
  assert.equal(env.owner.pending, null);
});
for (const age of [59999, 60000, 60001])
  test(`WR-040 TTL boundary ${age}`, (t) => {
    const env = pendingSetup(t);
    env.owner.send(payload(A), "A");
    env.time(age);
    env.setReady(true);
    env.owner.flush();
    assert.equal(env.sent.length, age < 60000 ? 1 : 0);
    if (age >= 60000) assert.equal(env.updates.at(-1)[1].reason, "expired");
  });
test("WR-041 cancel uses ID and cannot affect newer pending", (t) => {
  const env = pendingSetup(t);
  env.owner.send(payload(A), "A");
  env.owner.cancelPending(B);
  assert.equal(env.owner.pending.payload.request_id, A);
  env.owner.cancelPending(A);
  assert.equal(env.updates.at(-1)[1].reason, "cancelled");
  env.owner.send(payload(B), "B");
  env.owner.cancelPending(A);
  env.setReady(true);
  env.owner.flush();
  assert.deepEqual(env.sent, [payload(B)]);
});
test("WR-042 WR-043 auth invalidates pending and dispose prevents revival", (t) => {
  const env = pendingSetup(t);
  env.owner.send(payload(A), "A");
  env.setAllowed(false);
  env.owner.authenticationExpired();
  env.setReady(true);
  env.owner.flush();
  assert.equal(env.sent.length, 0);
  assert.equal(env.owner.send(payload(B), "B").reason, "not_connected");
  env.owner.dispose();
  env.setAllowed(true);
  assert.equal(env.owner.send(payload(B), "B").ok, false);
  env.owner.flush();
  assert.equal(env.sent.length, 0);
});
test("WR-046 WR-047 attempted uncertain request is never queued or retried", (t) => {
  for (const queued of [false, true]) {
    const env = pendingSetup(t);
    env.setReady(!queued);
    env.setResult("uncertain");
    const result = env.owner.send(payload(A), "A");
    if (queued) {
      env.setReady(true);
      env.owner.flush();
    } else assert.equal(result.reason, "uncertain");
    assert.equal(env.owner.pending, null);
    env.owner.disconnected();
    env.owner.flush();
    assert.equal(env.sent.length, 1);
    assert.equal(env.events.at(-1).type, "aborted");
  }
});
