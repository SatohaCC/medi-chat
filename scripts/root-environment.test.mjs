import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

for (const mode of ["development", "production"]) {
  test(`only root .env.local is shared in ${mode}; explicit environment wins`, () => {
    const root = mkdtempSync(join(tmpdir(), "medi-chat-root-env-"));
    try {
      for (const name of [".env", `.env.${mode}`, `.env.${mode}.local`]) {
        writeFileSync(join(root, name), "APP_SECRET_KEY=wrong\nIGNORED_ENV_TEST=wrong\n");
      }
      writeFileSync(join(root, ".env.local"), "APP_SECRET_KEY=correct\nROOT_ENV_BASE=local\nROOT_ENV_CHILD=${ROOT_ENV_BASE}/child\n");
      const script = fileURLToPath(new URL("root-environment.cjs", import.meta.url));
      const env = { ...process.env, NODE_ENV: mode, ROOT_ENV_BASE: "explicit" };
      for (const name of ["APP_SECRET_KEY", "IGNORED_ENV_TEST", "ROOT_ENV_CHILD"]) delete env[name];
      const output = execFileSync(process.execPath, ["-e", `require(process.argv[1]).loadRootEnvironment(process.argv[2]); console.log(JSON.stringify([process.env.APP_SECRET_KEY, process.env.IGNORED_ENV_TEST, process.env.ROOT_ENV_CHILD]))`, script, root], { env, encoding: "utf8" });
      assert.deepEqual(JSON.parse(output), ["correct", null, "explicit/child"]);
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });
}
