import assert from "node:assert/strict";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { safeSpawnSync } from "./safe-process.mjs";

test("Node runner times out one test and still executes the next", () => {
  const root = mkdtempSync(join(tmpdir(), "node-timeout-"));
  try {
    const path = join(root, "timeout.test.mjs");
    writeFileSync(path, `import test from 'node:test';
      test('stalled acceptance', async () => { await new Promise(r => setTimeout(r, 400)); });
      test('following acceptance', () => {});`);
    const env = { ...process.env };
    delete env.NODE_TEST_CONTEXT;
    const result = safeSpawnSync(process.execPath, ["scripts/checks/run-node-tests.mjs", "--test-timeout=100", path], { env, encoding: "utf8", timeout: 3000 });
    assert.ok(!result.error, result.error?.message);
    assert.equal(result.status, 1);
    assert.match(result.stdout, /testTimeoutFailure|timed out/);
    assert.match(result.stdout, /ok 2 - following acceptance/);
    // Node counts timed-out tests as cancelled and emits test:fail for them.
    assert.match(result.stdout, /# cancelled 1/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
