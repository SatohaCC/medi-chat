import assert from "node:assert/strict";
import test from "node:test";
import { safeExecuteAsync, safeSpawnSync } from "./safe-process.mjs";

for (const [name, execute] of [["async", safeExecuteAsync], ["sync", safeSpawnSync]]) {
  test(`${name} capture rejects output beyond maxBuffer on either stream`, async () => {
    for (const stream of ["stdout", "stderr"]) {
      const result = await execute(process.execPath, ["-e", `process.${stream}.write('あ'.repeat(1000))`], { maxBuffer: 128, timeout: 2000, encoding: "utf8" });
      assert.notEqual(result.status, 0);
      assert.equal(result.error?.code, "ENOBUFS");
      assert.ok(Buffer.byteLength(result[stream]) <= 128);
    }
  });

  test(`${name} capture stops a noisy live process before its timeout`, async () => {
    const result = await execute(process.execPath, ["-e", "process.stdout.write('x'.repeat(4096)); setInterval(() => process.stdout.write('x'), 10)"], { maxBuffer: 128, timeout: 2000 });
    assert.equal(result.error?.code, "ENOBUFS");
  });

  test(`${name} capture preserves successful stdout and stderr`, async () => {
    const result = await execute(process.execPath, ["-e", "console.log('ok'); console.error('diagnostic')"], { maxBuffer: 128, encoding: "utf8" });
    assert.equal(result.status, 0);
    assert.equal(result.stdout.trim(), "ok");
    assert.equal(result.stderr.trim(), "diagnostic");
  });
}
