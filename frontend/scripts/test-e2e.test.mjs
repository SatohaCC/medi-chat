import assert from "node:assert/strict";
import test from "node:test";
import { runE2e } from "./test-e2e.mjs";

test("normal entry requires configured readiness/OS health then mock and real", async () => {
  const calls = [];
  const result = await runE2e({
    run: async (layer) => {
      calls.push(layer);
      return 0;
    },
  });
  assert.equal(result, 0);
  assert.deepEqual(calls, ["configured", "mock", "real"]);
});

for (const failed of ["configured", "mock", "real"]) {
  test(`failure of required ${failed} layer is not hidden`, async () => {
    const calls = [];
    const result = await runE2e({
      run: async (layer) => {
        calls.push(layer);
        return layer === failed ? 7 : 0;
      },
    });
    assert.equal(result, 7);
    assert.equal(calls.at(-1), failed);
  });
}
