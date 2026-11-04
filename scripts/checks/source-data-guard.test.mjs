import assert from "node:assert/strict";
import test from "node:test";
import { findIgnoredSourceDataReferences, scanTestFiles } from "./source-data-guard.mjs";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

test("flags direct PMDA original and structured-data paths with locations", () => {
  const sourceDataDirectory = ["data", "pmda", "structured"].join("/");
  const originalDirectory = ["data", "pmda", "originals", "source.xml"].join("\\");
  const source = [
    `readFileSync("../../../../${sourceDataDirectory}/example/search_units.jsonl")`,
    `readFileSync("${originalDirectory}")`,
  ].join("\n");

  assert.deepEqual(findIgnoredSourceDataReferences("sample.test.mjs", source), [
    { file: "sample.test.mjs", line: 1 },
    { file: "sample.test.mjs", line: 2 },
  ]);
});

test("does not flag tracked fixtures, unrelated PMDA paths, or harmless mentions", () => {
  const source = [
    'readFileSync(new URL("./sample-evidence-units.json", import.meta.url))',
    'const localName = "data" + "/pmda/structured/example.jsonl";',
    'readFileSync("data/pmda/fixture/example.json")',
  ].join("\n");

  assert.deepEqual(findIgnoredSourceDataReferences("sample.test.mjs", source), []);
});

test("flags data paths built directly or stored before a file read", () => {
  const segment = (...codes) => String.fromCharCode(...codes);
  const dataSegments = [segment(100, 97, 116, 97), segment(112, 109, 100, 97), segment(115, 116, 114, 117, 99, 116, 117, 114, 101, 100)];
  const direct = `readFileSync(join(root, ${dataSegments.map(JSON.stringify).join(", ")}, "units.jsonl"));`;
  const assigned = [
    `const unitsPath = path.resolve(root, ${[
      segment(100, 97, 116, 97),
      segment(112, 109, 100, 97),
      segment(111, 114, 105, 103, 105, 110, 97, 108, 115),
    ].map(JSON.stringify).join(", ")}, "source.xml");`,
    'readFileSync(unitsPath, "utf8");',
  ].join("\n");

  assert.deepEqual(findIgnoredSourceDataReferences("direct.test.mjs", direct), [
    { file: "direct.test.mjs", line: 1 },
  ]);
  assert.deepEqual(findIgnoredSourceDataReferences("assigned.test.mjs", assigned), [
    { file: "assigned.test.mjs", line: 1 },
  ]);
});

test("scans only Node unit-test files and reports ignored data with repository-relative locations", () => {
  const root = mkdtempSync(join(tmpdir(), "source-data-guard-"));
  const testsDirectory = join(root, "frontend/features");
  mkdirSync(testsDirectory, { recursive: true });
  const directory = [
    String.fromCharCode(100, 97, 116, 97),
    String.fromCharCode(112, 109, 100, 97),
    String.fromCharCode(115, 116, 114, 117, 99, 116, 117, 114, 101, 100),
  ].join("/");
  const testPath = join(testsDirectory, "uses-local-data.test.mjs");
  const nonTestPath = join(testsDirectory, "explicit-source-data.mjs");
  writeFileSync(testPath, `readFileSync("${directory}/units.jsonl")\n`, "utf8");
  writeFileSync(nonTestPath, `readFileSync("${directory}/units.jsonl")\n`, "utf8");
  try {
    assert.deepEqual(scanTestFiles(root, ["frontend/features"]), [
      { file: "frontend/features/uses-local-data.test.mjs", line: 1 },
    ]);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
