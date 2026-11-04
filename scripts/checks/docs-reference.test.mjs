import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { dirname, relative, resolve } from "node:path";
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
const TRACKED_PATHS = new Set(
  execFileSync("git", ["ls-files", "-z"], { cwd: ROOT, encoding: "utf8" }).split("\0").filter(Boolean),
);

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
    .filter(({ target, absolute }) => {
      if (!target) return false;
      const relativeTarget = relative(ROOT, absolute).replaceAll("\\", "/").replace(/\/$/, "");
      const tracked = relativeTarget === ""
        || TRACKED_PATHS.has(relativeTarget)
        || [...TRACKED_PATHS].some((path) => path.startsWith(`${relativeTarget}/`));
      return !existsSync(absolute) || !tracked;
    });
  const obsoleteReferences = GUIDES.filter((file) =>
    readFileSync(resolve(ROOT, file), "utf8").includes(RETIRED_GUIDE_DIRECTORY),
  );

  assert.deepEqual(missing, []);
  assert.deepEqual(obsoleteReferences, []);
});
