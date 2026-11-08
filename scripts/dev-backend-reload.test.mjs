import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { resolve } from "node:path";
import test from "node:test";
import {
  BACKEND_DIR,
  DEFAULT_UVICORN_ARGS,
  RELOAD_EXCLUDED_DIRS,
} from "./dev-backend.mjs";

test("default uvicorn args keep the backend venv out of the reload watch", () => {
  assert.ok(DEFAULT_UVICORN_ARGS.includes("--reload"));

  const excludes = DEFAULT_UVICORN_ARGS.flatMap((arg, index, args) =>
    arg === "--reload-exclude" && args[index + 1] ? [args[index + 1]] : [],
  );
  const venv = RELOAD_EXCLUDED_DIRS[0];
  assert.ok(excludes.includes(venv), `unexpected excludes: ${excludes.join(", ")}`);
  assert.equal(venv, resolve(BACKEND_DIR, ".venv"));
  assert.ok(existsSync(venv), "reload exclude must point at an existing directory");
});
