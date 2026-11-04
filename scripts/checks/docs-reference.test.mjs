import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const ROOT = fileURLToPath(new URL("../../", import.meta.url));
const GUIDES = [
  "AGENTS.md",
  "scripts/README.md",
  "docs/development/validation.md",
  "docs/architecture/backend-design.md",
  "docs/development/authentication-validation.md",
  "docs/development/harness-strengthening-plan.md",
];
const RETIRED_GUIDE_DIRECTORY = [".agents", "lessons"].join("/");

function localMarkdownTargets(file) {
  const source = readFileSync(resolve(ROOT, file), "utf8");
  return [...source.matchAll(/\[[^\]]+\]\(([^)]+)\)/g)]
    .map((match) => match[1].trim().replace(/^<|>$/g, ""))
    .filter((target) => target && !target.startsWith("#") && !/^[a-z][a-z\d+.-]*:/i.test(target))
    .map((target) => ({
      source: file,
      target: target.split("#", 1)[0],
      absolute: resolve(ROOT, dirname(file), target.split("#", 1)[0]),
    }));
}

test("active work guides use current documentation without local lesson-system links", () => {
  const missing = GUIDES.flatMap(localMarkdownTargets)
    .filter(({ target, absolute }) => target && !existsSync(absolute));
  const obsoleteReferences = GUIDES.filter((file) =>
    readFileSync(resolve(ROOT, file), "utf8").includes(RETIRED_GUIDE_DIRECTORY),
  );

  assert.deepEqual(missing, []);
  assert.deepEqual(obsoleteReferences, []);
});
