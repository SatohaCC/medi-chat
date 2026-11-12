import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { dirname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { safeExecFileSync } from "./safe-process.mjs";

const ROOT = fileURLToPath(new URL("../../", import.meta.url));
const GUIDES = [
  "AGENTS.md",
  "scripts/README.md",
  "docs/development/validation.md",
  "docs/architecture/backend-design.md",
  "docs/development/authentication-validation.md",
  "docs/development/harness-strengthening-plan.md",
  ".agents/skills/feature-pipeline/SKILL.md",
  ".agents/skills/feature-pipeline/references/orchestration.md",
  ".agents/skills/feature-pipeline/references/agent-contract.md",
  ".agents/agents/planner.md",
  ".agents/agents/test-designer.md",
  ".agents/agents/generator.md",
  ".agents/agents/evaluator.md",
  ".agents/agents/test-writer.md",
];
const PIPELINE_FILES = [
  ".agents/skills/feature-pipeline/SKILL.md",
  ".agents/skills/feature-pipeline/references/orchestration.md",
  ".agents/skills/feature-pipeline/references/agent-contract.md",
  ".agents/agents/planner.md",
  ".agents/agents/test-designer.md",
  ".agents/agents/generator.md",
  ".agents/agents/evaluator.md",
  ".agents/agents/test-writer.md",
];
const RETIRED_GUIDE_DIRECTORY = [".agents", "lessons"].join("/");
const TRACKED_PATHS = new Set(
  safeExecFileSync("git", ["ls-files", "-z"], { cwd: ROOT, encoding: "utf8" }).split("\0").filter(Boolean),
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

test("feature-pipeline uses mechanical quality artifacts without PROGRESS_PATH overhead", () => {
  for (const file of PIPELINE_FILES) {
    const content = readFileSync(resolve(ROOT, file), "utf8");
    assert.equal(
      content.includes("PROGRESS_PATH"),
      false,
      `${file} must not require PROGRESS_PATH manual progress tracking`,
    );
    assert.equal(
      content.includes("for-llm/progress/"),
      false,
      `${file} must not reference for-llm/progress/ markdown logs`,
    );
  }
  const skill = readFileSync(resolve(ROOT, ".agents/skills/feature-pipeline/SKILL.md"), "utf8");
  const orchestration = readFileSync(resolve(ROOT, ".agents/skills/feature-pipeline/references/orchestration.md"), "utf8");
  assert.ok(skill.includes("PLAN_PATH"));
  assert.ok(skill.includes("TESTCASE_PATH"));
  assert.ok(skill.includes("tmp/quality/task.json"));
  assert.ok(orchestration.includes("tmp/quality/result.json"));
});

test("agent prompts and harness guides omit legacy transition rules and stay concise", () => {
  const retiredPhrases = [
    "USER_REVIEW_REQUIRED",
    "旧Writer/本番専任Generator",
    "legacyにあった旧グローバルhook",
  ];
  for (const file of ["AGENTS.md", "scripts/README.md", ...PIPELINE_FILES]) {
    const content = readFileSync(resolve(ROOT, file), "utf8");
    for (const phrase of retiredPhrases) {
      assert.equal(
        content.includes(phrase),
        false,
        `${file} still contains retired transition guidance: ${phrase}`,
      );
    }
  }
  const totalPromptChars = ["AGENTS.md", ...PIPELINE_FILES]
    .map((file) => readFileSync(resolve(ROOT, file), "utf8").replaceAll("\r\n", "\n").length)
    .reduce((sum, len) => sum + len, 0);
  assert.ok(
    totalPromptChars < 9000,
    `Expected concise prompt bundle (< 9000 chars), got ${totalPromptChars}`,
  );
});

test("generator role defaults to medium reasoning effort instead of fixed low", () => {
  const generator = readFileSync(resolve(ROOT, ".agents/agents/generator.md"), "utf8");
  const orchestration = readFileSync(
    resolve(ROOT, ".agents/skills/feature-pipeline/references/orchestration.md"),
    "utf8",
  );
  assert.match(generator, /model_reasoning_effort:\s*"medium"/);
  assert.equal(generator.includes('model_reasoning_effort: "low"'), false);
  assert.match(orchestration, /\|\s*Generator\s*\|\s*medium（既定）\s*\|/);
  assert.equal(orchestration.includes("low（固定）"), false);
});
