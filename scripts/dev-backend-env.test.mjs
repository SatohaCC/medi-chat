import assert from "node:assert/strict";
import { resolve } from "node:path";
import test from "node:test";
import { defaultSpawnEnvironment, PROJECT_ROOT } from "./dev-backend.mjs";

test("dev backend uses the repository uv cache when none is configured", () => {
  const environment = defaultSpawnEnvironment({ PATH: "C:\\bin" });

  assert.equal(environment.UV_CACHE_DIR, resolve(PROJECT_ROOT, ".uv-cache"));
  assert.equal(environment.PATH, "C:\\bin");
});

test("dev backend keeps an explicitly configured uv cache", () => {
  const environment = defaultSpawnEnvironment({
    UV_CACHE_DIR: "C:\\custom-uv-cache",
  });

  assert.equal(environment.UV_CACHE_DIR, "C:\\custom-uv-cache");
});

test("dev backend does not mutate the parent environment", () => {
  const parent = { PATH: "C:\\bin" };
  defaultSpawnEnvironment(parent);

  assert.deepEqual(parent, { PATH: "C:\\bin" });
});
