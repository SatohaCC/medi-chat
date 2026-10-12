import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");

function resolvePython() {
  const venvPython =
    process.platform === "win32"
      ? resolve(root, "backend/.venv/Scripts/python.exe")
      : resolve(root, "backend/.venv/bin/python");
  if (existsSync(venvPython)) {
    return { command: venvPython, prefixArgs: [] };
  }
  return {
    command: "uv",
    prefixArgs: ["run", "--project", resolve(root, "backend"), "python"],
  };
}

test("SX-R13: immutable semantic oracle rejects all content/structure mutations", () => {
  const { command, prefixArgs } = resolvePython();
  const output = execFileSync(
    command,
    [
      ...prefixArgs,
      resolve(root, "frontend/scripts/semantic-compare.py"),
      "controls",
      resolve(root, "frontend/e2e-real/fixtures/import-semantic-oracle.json"),
    ],
    { cwd: root, encoding: "utf8" },
  );
  const observed = JSON.parse(output);
  assert.equal(observed.count, 19);
  assert.deepEqual(observed.negative_controls, [
    "body-deletion",
    "body-change",
    "body-addition",
    "body-duplication",
    "body-order",
    "cell-value",
    "cell-grid",
    "cell-rowspan",
    "cell-colspan",
    "html-header",
    "html-scope",
    "reference-target",
    "reference-order",
    "section-deletion",
    "section-duplication",
    "source-sha",
    "context",
    "columns",
    "figure",
  ]);
});
