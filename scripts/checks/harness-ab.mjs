// Run isolated A/B evaluations comparing two Git commits/refs of the agent harness.
// Reuses clean-checkout worktree isolation and harness-metrics telemetry.
import { spawn, spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { summarizeHarnessMetrics } from "./harness-metrics.mjs";
import { createCleanWorktree } from "./verify-clean-checkout.mjs";
import { safeExecuteAsync, safeSpawnSync } from "./safe-process.mjs";

export const ROOT = fileURLToPath(new URL("../../", import.meta.url));

function collectPromptFiles(worktreePath) {
  const candidates = ["AGENTS.md", ".agents/skills/feature-pipeline/SKILL.md"];
  const referencesDir = join(worktreePath, ".agents/skills/feature-pipeline/references");
  if (existsSync(referencesDir)) {
    for (const entry of readdirSync(referencesDir, { withFileTypes: true })) {
      if (entry.isFile() && entry.name.endsWith(".md")) {
        candidates.push(`.agents/skills/feature-pipeline/references/${entry.name}`);
      }
    }
  }
  const agentsDir = join(worktreePath, ".agents/agents");
  if (existsSync(agentsDir)) {
    for (const entry of readdirSync(agentsDir, { withFileTypes: true })) {
      if (entry.isFile() && entry.name.endsWith(".md")) {
        candidates.push(`.agents/agents/${entry.name}`);
      }
    }
  }
  return candidates.filter((rel) => existsSync(join(worktreePath, rel))).sort();
}

export function measurePromptBundleChars(worktreePath) {
  const files = collectPromptFiles(worktreePath);
  const breakdown = {};
  let totalChars = 0;
  for (const rel of files) {
    const length = readFileSync(join(worktreePath, rel), "utf8").replaceAll("\r\n", "\n").length;
    breakdown[rel] = length;
    totalChars += length;
  }
  return { totalChars, fileCount: files.length, breakdown };
}

function collectGitDiffSummary(worktreePath) {
  const status = safeSpawnSync("git", ["status", "--short"], {
    cwd: worktreePath,
    encoding: "utf8",
    windowsHide: true,
  });
  const files = status.status === 0
    ? status.stdout.split(/\r?\n/).filter(Boolean)
    : [];
  return { changedCount: files.length, files };
}

export function compareHarnessRuns(baseArm, headArm) {
  return {
    promptCharsDelta: headArm.prompt.totalChars - baseArm.prompt.totalChars,
    durationMsDelta: headArm.durationMs - baseArm.durationMs,
    checkDurationMsDelta:
      headArm.metrics.reports.totalCheckDurationMs - baseArm.metrics.reports.totalCheckDurationMs,
    blockRateDelta: Number(
      (headArm.metrics.stop.blockRate - baseArm.metrics.stop.blockRate).toFixed(4),
    ),
    stagnatedDelta: headArm.metrics.stop.stagnated - baseArm.metrics.stop.stagnated,
    editWarningsDelta:
      headArm.metrics.edits.editLoopWarnings - baseArm.metrics.edits.editLoopWarnings,
  };
}

function appendRollingTail(current, chunk, maxChars = 4000) {
  const combined = current + chunk;
  return combined.length > maxChars ? combined.slice(-maxChars) : combined;
}

function terminateProcessTree(child) {
  if (!child?.pid) return;
  if (process.platform === "win32") {
    const res = spawnSync("taskkill", ["/PID", String(child.pid), "/T", "/F"], {
      stdio: "ignore",
      windowsHide: true,
    });
    if (res.error || res.status !== 0) {
      try {
        child.kill();
      } catch {
        // Ignore already exited process
      }
    }
    return;
  }
  try {
    process.kill(-child.pid, "SIGTERM");
  } catch {
    try {
      child.kill("SIGTERM");
    } catch {
      // Ignore already exited process
    }
  }
  const killTimer = setTimeout(() => {
    try {
      process.kill(-child.pid, "SIGKILL");
    } catch {
      try {
        child.kill("SIGKILL");
      } catch {
        // Ignore already exited process
      }
    }
  }, 150);
  killTimer.unref?.();
}

async function runCommandInWorktree(command, worktreePath, { env = {}, timeoutMs = 1_800_000 } = {}) {
  const started = Date.now();
  const result = await safeExecuteAsync(command, {
    cwd: worktreePath,
    shell: true,
    windowsHide: true,
    env: { ...process.env, ...env },
    timeout: timeoutMs > 0 ? timeoutMs : undefined,
    tailMaxChars: 4000,
    // Evaluations retain only the tail; cumulative log volume is not a failure.
    maxBuffer: Infinity,
  });
  return {
    durationMs: Date.now() - started,
    exitCode: result.status ?? 1,
    error: result.error instanceof Error ? result.error.message : result.error,
    stdoutTail: result.stdout,
    stderrTail: result.stderr,
  };
}

export async function evaluateArm({
  root = ROOT,
  label,
  ref,
  command,
  taskPrompt = "",
  transcriptName = null,
  keepWorktree = false,
  timeoutMs = 1_800_000,
}) {
  const worktree = createCleanWorktree(root, ref);
  let armResult;
  try {
    const prompt = measurePromptBundleChars(worktree.path);
    const execResult = command
      ? await runCommandInWorktree(command, worktree.path, {
          timeoutMs,
          env: {
            HARNESS_AB_ARM: label,
            HARNESS_AB_REF: ref,
            HARNESS_AB_COMMIT: worktree.revision,
            HARNESS_AB_WORKTREE: worktree.path,
            ...(taskPrompt ? { HARNESS_TASK_PROMPT: taskPrompt } : {}),
          },
        })
      : { durationMs: 0, exitCode: 0, error: null, stdoutTail: "", stderrTail: "" };

    const transcriptPath = transcriptName ? join(worktree.path, transcriptName) : null;
    const metrics = summarizeHarnessMetrics({
      hooksDir: join(worktree.path, ".agents/work/.hooks"),
      qualityDir: join(worktree.path, "tmp/quality"),
      transcriptPath: transcriptPath && existsSync(transcriptPath) ? transcriptPath : null,
    });
    const diff = collectGitDiffSummary(worktree.path);

    armResult = {
      label,
      ref,
      commit: worktree.revision,
      worktreePath: keepWorktree ? worktree.path : null,
      prompt,
      ...execResult,
      metrics,
      diff,
    };
  } finally {
    if (!keepWorktree) {
      worktree.cleanup();
    }
  }
  return armResult;
}

export async function runAbEvaluation({
  root = ROOT,
  baseRef,
  headRef = "HEAD",
  command = null,
  taskPrompt = "",
  transcriptName = null,
  keepWorktree = false,
  timeoutMs = 1_800_000,
  reportPath = null,
}) {
  if (!baseRef) throw new Error("--base <ref> is required");
  const base = await evaluateArm({
    root,
    label: "base",
    ref: baseRef,
    command,
    taskPrompt,
    transcriptName,
    keepWorktree,
    timeoutMs,
  });
  const head = await evaluateArm({
    root,
    label: "head",
    ref: headRef,
    command,
    taskPrompt,
    transcriptName,
    keepWorktree,
    timeoutMs,
  });
  const report = {
    version: 1,
    createdAt: new Date().toISOString(),
    taskPrompt: taskPrompt || null,
    command: command || null,
    base,
    head,
    delta: compareHarnessRuns(base, head),
  };

  if (reportPath) {
    const resolved = resolve(root, reportPath);
    mkdirSync(resolve(resolved, ".."), { recursive: true });
    writeFileSync(resolved, JSON.stringify(report, null, 2));
  }
  return report;
}

export function formatAbSummary(report) {
  const { base, head, delta } = report;
  const lines = [
    `[harness-ab] Base (${base.ref} @ ${base.commit.slice(0, 8)}) vs Head (${head.ref} @ ${head.commit.slice(0, 8)})`,
    `[harness-ab] Prompt chars: ${base.prompt.totalChars} -> ${head.prompt.totalChars} (${delta.promptCharsDelta >= 0 ? "+" : ""}${delta.promptCharsDelta})`,
    `[harness-ab] Duration: ${(base.durationMs / 1000).toFixed(2)}s -> ${(head.durationMs / 1000).toFixed(2)}s (${delta.durationMsDelta >= 0 ? "+" : ""}${(delta.durationMsDelta / 1000).toFixed(2)}s)`,
    `[harness-ab] Exit code: base=${base.exitCode}, head=${head.exitCode}`,
    `[harness-ab] Check duration: ${(base.metrics.reports.totalCheckDurationMs / 1000).toFixed(2)}s -> ${(head.metrics.reports.totalCheckDurationMs / 1000).toFixed(2)}s (${delta.checkDurationMsDelta >= 0 ? "+" : ""}${(delta.checkDurationMsDelta / 1000).toFixed(2)}s)`,
    `[harness-ab] Stop blockRate: ${(base.metrics.stop.blockRate * 100).toFixed(1)}% -> ${(head.metrics.stop.blockRate * 100).toFixed(1)}% (${delta.blockRateDelta >= 0 ? "+" : ""}${(delta.blockRateDelta * 100).toFixed(1)}%)`,
    `[harness-ab] Stagnated: ${base.metrics.stop.stagnated} -> ${head.metrics.stop.stagnated} | Changed files: ${base.diff.changedCount} -> ${head.diff.changedCount}`,
  ];
  if (base.worktreePath || head.worktreePath) {
    lines.push(`[harness-ab] Kept worktrees: base=${base.worktreePath}, head=${head.worktreePath}`);
  }
  return lines.join("\n");
}

function parseArgs(args) {
  const opts = {
    baseRef: null,
    headRef: "HEAD",
    command: null,
    taskPrompt: "",
    transcriptName: null,
    keepWorktree: false,
    timeoutMs: 1_800_000,
    reportPath: null,
    json: false,
  };
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === "--base") opts.baseRef = args[++i];
    else if (arg === "--head") opts.headRef = args[++i];
    else if (arg === "--cmd") opts.command = args[++i];
    else if (arg === "--prompt") opts.taskPrompt = args[++i];
    else if (arg === "--transcript-name") opts.transcriptName = args[++i];
    else if (arg === "--report") opts.reportPath = args[++i];
    else if (arg === "--timeout-ms") opts.timeoutMs = Number(args[++i]);
    else if (arg === "--keep") opts.keepWorktree = true;
    else if (arg === "--json") opts.json = true;
    else {
      throw new Error(
        "Usage: node scripts/checks/harness-ab.mjs --base <ref> [--head <ref>] [--cmd <shell-cmd>] [--prompt <text>] [--report <path>] [--keep] [--json]",
      );
    }
  }
  return opts;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const opts = parseArgs(process.argv.slice(2));
    const defaultReport = opts.reportPath ?? `tmp/quality/harness-ab-${Date.now()}.json`;
    const report = await runAbEvaluation({ ...opts, reportPath: defaultReport });
    if (opts.json) {
      console.log(JSON.stringify(report, null, 2));
    } else {
      console.log(formatAbSummary(report));
      console.log(`[harness-ab] Report: ${relative(ROOT, resolve(ROOT, defaultReport)).replaceAll("\\", "/")}`);
    }
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 2;
  }
}
