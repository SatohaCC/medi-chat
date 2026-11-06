import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire, stripTypeScriptTypes } from "node:module";
import test from "node:test";
import { pathToFileURL } from "node:url";

const require = createRequire(import.meta.url);
const { NextRequest } = require("next/server");
const source = readFileSync(new URL("../proxy.ts", import.meta.url), "utf8").replace(
  '"next/server"',
  JSON.stringify(pathToFileURL(require.resolve("next/server.js")).href),
);
const { proxy } = await import(
  `data:text/javascript;base64,${Buffer.from(stripTypeScriptTypes(source)).toString("base64")}`
);

for (const cookie of ["", "medi_chat_access_token=test-token"]) {
  test(`proxy prohibits caching and referrer disclosure with ${cookie ? "a cookie" : "no cookie"}`, () => {
    const response = proxy(
      new NextRequest("https://example.invalid/login", { headers: { cookie } }),
    );
    assert.equal(response.headers.get("cache-control"), "private, no-store");
    assert.equal(response.headers.get("referrer-policy"), "no-referrer");
    // This checks the Proxy output; production Next.js composes Vary separately.
    assert.equal(response.headers.get("vary"), "Cookie");
  });
}
