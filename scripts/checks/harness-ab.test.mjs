import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { compareHarnessRuns, formatAbSummary, measurePromptBundleChars, runAbEvaluation } from "./harness-ab.mjs";

function createHarnessHistoryRepo() {
  const root = mkdtempSync(join(tmpdir(), "harness-ab-git-"));
  const git = (...args) => execFileSync("git", args, { cwd: root, stdio: "pipe" });
  git("init", "--quiet");
  git("config", "user.name", "AB Test");
  git("config", "user.email", "ab@example.invalid");

  // Commit 1: verbose base harness
  mkdirSync(join(root, ".agents/agents"), { recursive: true });
  mkdirSync(join(root, ".agents/skills/feature-pipeline/references"), { recursive: true });
  writeFileSync(join(root, ".gitignore"), ".agents/work/\ntmp/\n", "utf8");
  writeFileSync(join(root, "AGENTS.md"), "base instructions " + "x".repeat(400), "utf8");
  writeFileSync(join(root, ".agents/skills/feature-pipeline/SKILL.md"), "base skill " + "y".repeat(300), "utf8");
  writeFileSync(join(root, ".agents/agents/generator.md"), 'model_reasoning_effort: "low"\n', "utf8");
  git("add", ".");
  git("commit", "--quiet", "--no-verify", "-m", "base harness");
  const baseCommit = git("rev-parse", "HEAD").toString("utf8").trim();

  // Commit 2: concise head harness
  writeFileSync(join(root, "AGENTS.md"), "lite instructions", "utf8");
  writeFileSync(join(root, ".agents/skills/feature-pipeline/SKILL.md"), "lite skill", "utf8");
  writeFileSync(join(root, ".agents/agents/generator.md"), 'model_reasoning_effort: "medium"\n', "utf8");
  git("add", ".");
  git("commit", "--quiet", "--no-verify", "-m", "lite harness");
  const headCommit = git("rev-parse", "HEAD").toString("utf8").trim();

  return { root, git, baseCommit, headCommit };
}

test("compareHarnessRuns computes deltas between base and head arms", () => {
  const baseArm = {
    ref: "base",
    commit: "111111111111",
    prompt: { totalChars: 12000 },
    durationMs: 10000,
    exitCode: 0,
    metrics: {
      reports: { totalCheckDurationMs: 25000 },
      stop: { blockRate: 0.5, stagnated: 1 },
      edits: { editLoopWarnings: 2 },
    },
    diff: { changedCount: 3 },
  };
  const headArm = {
    ref: "head",
    commit: "222222222222",
    prompt: { totalChars: 8000 },
    durationMs: 6000,
    exitCode: 0,
    metrics: {
      reports: { totalCheckDurationMs: 9000 },
      stop: { blockRate: 0, stagnated: 0 },
      edits: { editLoopWarnings: 0 },
    },
    diff: { changedCount: 2 },
  };
  const delta = compareHarnessRuns(baseArm, headArm);
  assert.deepEqual(delta, {
    promptCharsDelta: -4000,
    durationMsDelta: -4000,
    checkDurationMsDelta: -16000,
    blockRateDelta: -0.5,
    stagnatedDelta: -1,
    editWarningsDelta: -2,
  });
  const text = formatAbSummary({ base: baseArm, head: headArm, delta });
  assert.match(text, /Prompt chars: 12000 -> 8000 \(-4000\)/);
  assert.match(text, /Stop blockRate: 50\.0% -> 0\.0% \(-50\.0%\)/);
});

test("runAbEvaluation runs isolated worktrees for base and head, collects metrics, and cleans up", () => {
  const { root, git, baseCommit, headCommit } = createHarnessHistoryRepo();
  try {
    const runnerScript = [
      "const fs = require('node:fs');",
      "fs.mkdirSync('.agents/work/.hooks', { recursive: true });",
      "const isBase = process.env.HARNESS_AB_ARM === 'base';",
      "fs.writeFileSync('.agents/work/.hooks/turn.json', JSON.stringify({ signature: 's', status: isBase ? 'failed' : 'passed', result: isBase ? 1 : 0, attempts: isBase ? 2 : 1 }));",
      "fs.writeFileSync('.agents/work/.hooks/turn.report.json', JSON.stringify({ version: 1, status: 'passed', tasks: [{ label: 'Quick', status: 'passed', durationMs: isBase ? 4000 : 500 }] }));",
      "fs.writeFileSync('output.txt', process.env.HARNESS_TASK_PROMPT || 'done');",
    ].join(" ");
    const reportPath = join(root, "tmp/ab-report.json");

    const report = runAbEvaluation({
      root,
      baseRef: baseCommit,
      headRef: headCommit,
      command: `${JSON.stringify(process.execPath)} -e ${JSON.stringify(runnerScript)}`,
      taskPrompt: "solve-task",
      reportPath,
    });

    assert.equal(existsSync(reportPath), true);
    const saved = JSON.parse(readFileSync(reportPath, "utf8"));
    assert.equal(saved.base.commit, baseCommit);
    assert.equal(saved.head.commit, headCommit);
    assert.ok(saved.base.prompt.totalChars > saved.head.prompt.totalChars);
    assert.equal(saved.base.metrics.stop.blockRate, 1);
    assert.equal(saved.head.metrics.stop.blockRate, 0);
    assert.equal(saved.delta.checkDurationMsDelta, -3500);
    assert.equal(saved.base.diff.changedCount, 1);
    assert.equal(saved.head.diff.changedCount, 1);

    // Worktrees must be removed after evaluation
    const worktrees = git("worktree", "list", "--porcelain").toString("utf8");
    assert.equal(worktrees.split("\nworktree ").length, 1);

    // Prompt measurement directly on root matches head commit
    assert.equal(measurePromptBundleChars(root).totalChars, saved.head.prompt.totalChars);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
