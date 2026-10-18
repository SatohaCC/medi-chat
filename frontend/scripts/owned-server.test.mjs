import assert from "node:assert/strict";
import test from "node:test";
import { ensureOwnedRestartPortAvailable, hasPortListener } from "./owned-server.mjs";

test("native listener observation distinguishes port, IPv6 and TIME_WAIT", () => {
  assert.equal(
    hasPortListener("TCP 127.0.0.1:3211 127.0.0.1:5555 TIME_WAIT 0", 3211),
    false,
  );
  assert.equal(hasPortListener("TCP 0.0.0.0:3211 0.0.0.0:0 LISTENING 123", 3211), true);
  assert.equal(hasPortListener("TCP [::]:3211 [::]:0 LISTENING 123", 3211), true);
  assert.equal(
    hasPortListener("TCP 127.0.0.1:13211 0.0.0.0:0 LISTENING 123", 3211),
    false,
  );
});

test("owned restart permits TIME_WAIT without a listener", async () => {
  await ensureOwnedRestartPortAvailable(3211, async () => false);
});
test("owned restart refuses a new listener and never stops it", async () => {
  await assert.rejects(
    ensureOwnedRestartPortAvailable(3211, async () => true),
    /occupied/,
  );
});
