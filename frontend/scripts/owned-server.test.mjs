import assert from "node:assert/strict";
import test from "node:test";
import { ensureOwnedRestartPortAvailable } from "./owned-server.mjs";

test("owned restart permits TIME_WAIT without a listener", async () => {
  await ensureOwnedRestartPortAvailable(3211, async () => false);
});
test("owned restart refuses a new listener and never stops it", async () => {
  await assert.rejects(
    ensureOwnedRestartPortAvailable(3211, async () => true),
    /occupied/,
  );
});
