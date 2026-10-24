import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { stripTypeScriptTypes } from "node:module";
import test from "node:test";

let sequence = 0;
async function moduleFor(t, handler, locks = true) {
  const original = Object.getOwnPropertyDescriptor(globalThis, "navigator");
  let tail = Promise.resolve();
  Object.defineProperty(globalThis, "navigator", {
    configurable: true,
    value: {
      locks: locks
        ? {
            request(_name, operation) {
              const next = tail.then(operation);
              tail = next.catch(() => {});
              return next;
            },
          }
        : undefined,
    },
  });
  t.after(() => {
    if (original) Object.defineProperty(globalThis, "navigator", original);
    else delete globalThis.navigator;
  });
  t.mock.method(globalThis, "fetch", handler);
  return fresh();
}

async function fresh() {
  const source = readFileSync(
    new URL("./authentication.ts", import.meta.url),
    "utf8",
  ).replace(
    '"./endpoints"',
    JSON.stringify(new URL("./endpoints.ts", import.meta.url).href),
  );
  const code = `${stripTypeScriptTypes(source)}\n// instance ${++sequence}`;
  return import(`data:text/javascript;base64,${Buffer.from(code).toString("base64")}`);
}

const principal = () => ({
  user_id: "test-user",
  expires_at: Math.floor(Date.now() / 1000) + 1800,
});
const json = (data, status = 200) => Response.json(data, { status });

test("cached access identity does not add a request for each API operation", async (t) => {
  let checks = 0;
  const auth = await moduleFor(t, async (url) => {
    if (String(url).endsWith("/me")) {
      checks++;
      return json(principal());
    }
    return json({ ok: true });
  });
  for (let index = 0; index < 10; index++) await auth.authenticatedFetch("/api/search");
  assert.equal(checks, 1);
});

test("simultaneous requests share one refresh", async (t) => {
  let valid = false,
    rotations = 0;
  const auth = await moduleFor(t, async (url) => {
    if (String(url).endsWith("/refresh")) {
      rotations++;
      valid = true;
      return json(principal());
    }
    return valid ? json(principal()) : json({}, 401);
  });
  await Promise.all(Array.from({ length: 20 }, () => auth.ensureAuthenticated()));
  assert.equal(rotations, 1);
});

test("separate tabs recheck shared cookies after acquiring the refresh lock", async (t) => {
  let valid = false,
    rotations = 0;
  const first = await moduleFor(t, async (url) => {
    if (String(url).endsWith("/refresh")) {
      rotations++;
      valid = true;
      return json(principal());
    }
    return valid ? json(principal()) : json({}, 401);
  });
  const second = await fresh();
  await Promise.all([first.ensureAuthenticated(), second.ensureAuthenticated()]);
  assert.equal(rotations, 1);
});

for (const status of [403, 503])
  test(`status ${status} does not cause refresh loops`, async (t) => {
    let requests = 0;
    const auth = await moduleFor(t, async () => {
      requests++;
      return json({}, status);
    });
    await assert.rejects(auth.ensureAuthenticated());
    assert.equal(requests, 1);
  });

test("mutations are not automatically replayed after a 401", async (t) => {
  let writes = 0;
  const auth = await moduleFor(t, async (url, options) => {
    if (String(url).includes("/api/auth/")) return json(principal());
    writes++;
    assert.equal(new Headers(options.headers).get("X-Medi-Chat-CSRF"), "1");
    return json({}, 401);
  });
  await assert.rejects(
    auth.authenticatedFetch("/api/attachment-imports", {
      method: "POST",
      body: "original",
    }),
  );
  assert.equal(writes, 1);
});

test("without cross-tab locks expired sessions require login", async (t) => {
  let requests = 0;
  const auth = await moduleFor(
    t,
    async () => {
      requests++;
      return json({}, 401);
    },
    false,
  );
  await assert.rejects(auth.ensureAuthenticated());
  assert.equal(requests, 1);
});

test("refresh response loss is not retried", async (t) => {
  let rotations = 0;
  const auth = await moduleFor(t, async (url) => {
    if (String(url).endsWith("/refresh")) {
      rotations++;
      throw new TypeError("network lost");
    }
    return json({}, 401);
  });
  await assert.rejects(auth.ensureAuthenticated());
  assert.equal(rotations, 1);
});

test("returnTo only navigates inside this application", async (t) => {
  const auth = await moduleFor(t, async () => json(principal()));
  for (const input of [
    null,
    "https://evil.invalid",
    "//evil.invalid",
    "/\\evil.invalid",
    "/login",
    "/\n/evil.invalid",
  ]) {
    assert.equal(auth.safeReturnTo(input), "/");
  }
  assert.equal(auth.safeReturnTo("/search?q=test"), "/search?q=test");
});
