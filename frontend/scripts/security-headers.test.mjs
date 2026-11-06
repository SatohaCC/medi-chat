import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { stripTypeScriptTypes } from "node:module";
import test from "node:test";

// The production config loads dotenv only outside Vercel. Use the deployment
// branch while importing the real config so developer secrets are not loaded.
test("Next.js applies browser security headers to all routes", async (t) => {
  const original = process.env.PYTHON_DOTENV_DISABLED;
  process.env.PYTHON_DOTENV_DISABLED = "1";
  t.after(() => {
    if (original === undefined) delete process.env.PYTHON_DOTENV_DISABLED;
    else process.env.PYTHON_DOTENV_DISABLED = original;
  });
  const source = readFileSync(new URL("../next.config.ts", import.meta.url), "utf8");
  const { default: config } = await import(
    `data:text/javascript;base64,${Buffer.from(stripTypeScriptTypes(source)).toString("base64")}`
  );
  const rules = await config.headers();
  assert.equal(rules.length, 1);
  assert.equal(rules[0].source, "/:path*");
  assert.deepEqual(
    Object.fromEntries(rules[0].headers.map(({ key, value }) => [key, value])),
    {
      "X-Frame-Options": "DENY",
      "X-Content-Type-Options": "nosniff",
      "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    },
  );
});
