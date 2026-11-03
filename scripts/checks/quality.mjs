// Shared, read-only quality entry point for manual runs, CI and Codex hooks.
import { spawnSync } from "node:child_process";
import { mkdirSync, readdirSync, writeFileSync } from "node:fs";
import { resolve, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { loadSpecification, registeredSuite } from "./quality-spec.mjs";
import { acceptanceEvidence, failureFeedback } from "./quality-feedback.mjs";

export const ROOT = fileURLToPath(new URL("../../", import.meta.url));

export function scopesFor(paths) {
  const scopes = new Set();
  for (const path of paths) {
    if (/^(package\.json|pnpm-lock\.yaml|pnpm-workspace\.yaml|\.nvmrc|\.python-version|pyrightconfig\.json)$/.test(path) || path.startsWith(".github/")) {
      for (const scope of ["backend", "frontend", "scripts"]) scopes.add(scope);
    }
    if (path.startsWith("backend/")) scopes.add("backend");
    if (path === "pytest.ini") {
      scopes.add("backend");
      scopes.add("scripts");
    }
    if (path.startsWith("frontend/")) scopes.add("frontend");
    if (path.startsWith("scripts/") || path.startsWith(".codex/")) scopes.add("scripts");
    if (path.startsWith("scripts/checks/") || path.startsWith("scripts/hooks/")) scopes.add("backend");
  }
  return [...scopes].sort();
}

function nodeTests(folder) {
  return readdirSync(resolve(ROOT, folder), { recursive: true, withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith(".test.mjs"))
    .map((entry) => relative(ROOT, resolve(entry.parentPath, entry.name)).replaceAll("\\", "/"))
    .sort();
}

export function planFor(scopes, phase = "full", { includeBackendStartup = false } = {}) {
  const plan = [];
  const pnpm = (label, ...args) => plan.push({ label, command: "pnpm", args });
  const uv = (label, ...args) => plan.push({ label, command: "uv", args: ["run", "--project", "backend", "--locked", ...args] });
  const node = (label, args) => plan.push({ label, command: process.execPath, args });
  if (scopes.includes("backend")) {
    if (phase === "quick") {
      uv("Python lint", "ruff", "check", "backend", "scripts/checks", "scripts/hooks");
      uv("Backend Mypy", "mypy", "--config-file", "backend/pyproject.toml", "--no-incremental", "-p", "backend");
    } else {
      if (includeBackendStartup) {
        const suite = registeredSuite("backend-startup");
        plan.push({
          label: "Configured backend startup and OS health",
          command: suite.command,
          args: [...suite.args],
          layer: "backend-startup",
          testRunner: suite.testRunner,
          requireEvidence: true,
        });
      }
      pnpm("Backend lint and architecture", "--filter", "backend", "lint");
      uv("Backend format", "ruff", "format", "--check", "backend", "scripts/checks", "scripts/hooks");
      pnpm("Python types (Pyright and mypy)", "typecheck:python");
      pnpm("Backend tests without DB/private sources", "test:backend", "-m", "not source_data", "-q");
    }
  }
  if (scopes.includes("frontend")) {
    pnpm("Frontend lint", "--filter", "frontend", "lint");
    if (phase === "full") {
      pnpm("Frontend format", "--filter", "frontend", "exec", "biome", "format", ".");
      pnpm("StyleX lint", "--filter", "frontend", "lint:stylex");
      pnpm("Frontend types", "typecheck:frontend");
      const tests = ["frontend/features", "frontend/shared", "frontend/scripts"].flatMap(nodeTests);
      node("Frontend unit tests", ["--experimental-strip-types", "--test", "--test-timeout=60000", ...tests]);
    }
  }
  if (scopes.includes("scripts")) {
    if (phase === "full") node("Development tooling tests", ["--test", "--test-timeout=60000", ...nodeTests("scripts")]);
    else node("Quality runner syntax", ["--check", "scripts/checks/quality.mjs"]);
    uv("Tooling lint", "ruff", "check", "scripts/checks", "scripts/hooks");
    if (phase === "full") {
      uv("Tooling format", "ruff", "format", "--check", "scripts/checks", "scripts/hooks");
      pnpm("Tooling types (Pyright and mypy)", "typecheck:scripts");
      uv("Hook regression tests", "python", "-m", "pytest", "scripts/hooks/test_quality_gate.py", "scripts/hooks/test_privacy_gate.py", "-q");
      pnpm("Generated requirements", "vercel:requirements:check");
      uv("Generated search guide", "python", "-m", "backend.infrastructure.cli.export_search_guide", "--check");
    }
  }
  return plan;
}

export function buildQualityPlan(scopes, specification, phase = "full", changed = false) {
  const combinedScopes = [...new Set([...scopes, ...specification.scopes])];
  const explicitlySelectedStartup = specification.tasks.some((task) => task.layer === "backend-startup");
  const includeBackendStartup = changed
    && phase === "full"
    && combinedScopes.includes("backend")
    && !explicitlySelectedStartup;
  return [
    ...specification.tasks,
    ...planFor(combinedScopes, phase, { includeBackendStartup }),
  ];
}

export function changedPaths(root = ROOT) {
  const collect = (args) => {
    const result = spawnSync("git", args, { cwd: root, encoding: "utf8" });
    if (result.status !== 0) throw new Error(result.stderr || "Cannot inspect Git changes");
    return result.stdout.split("\0").filter(Boolean);
  };
  return [...new Set([
    ...collect(["diff", "HEAD", "--name-only", "-z", "--no-renames"]),
    ...collect(["ls-files", "--others", "--exclude-standard", "-z"]),
  ])].sort();
}

export function runPlan(plan, execute = spawnSync, reportPath = null) {
  let failed = false;
  const report = {
    version: 1,
    status: "not_run",
    excludedLayers: ["backend-startup", "postgres", "browser", "external_api"]
      .filter((layer) => !plan.some((task) => task.layer === layer)),
    tasks: plan.map((task) => ({ ...task, status: "not_run", exitCode: null, durationMs: 0 })),
  };
  const save = () => {
    if (reportPath) writeFileSync(reportPath, JSON.stringify(report, null, 2));
  };
  save();
  const temporary = resolve(ROOT, "tmp/quality");
  mkdirSync(temporary, { recursive: true });
  for (const [index, task] of plan.entries()) {
    console.log(`\n[quality] ${task.label}`);
    const invocation = invocationFor(task);
    const started = Date.now();
    const result = execute(invocation.command, invocation.args, {
      cwd: ROOT,
      stdio: "pipe",
      encoding: "utf8",
      maxBuffer: 16 * 1024 * 1024,
      shell: invocation.shell,
      timeout: 300_000,
      env: { ...process.env, UV_CACHE_DIR: resolve(ROOT, ".uv-cache"), TMP: temporary, TEMP: temporary, TMPDIR: temporary },
    });
    if (result.stdout) process.stdout.write(result.stdout);
    if (result.stderr) process.stderr.write(result.stderr);
    Object.assign(report.tasks[index], {
      status: result.error?.code === "ETIMEDOUT" ? "timeout"
        : result.error ? "start_error" : result.status === 0 ? "passed" : "failed",
      exitCode: result.status ?? null,
      durationMs: Date.now() - started,
    });
    const output = `${result.stdout ?? ""}\n${result.stderr ?? ""}`;
    if (task.requireEvidence && report.tasks[index].status === "passed") {
      const evidence = acceptanceEvidence(output, task.testRunner);
      report.tasks[index].evidence = evidence;
      if (!evidence.passed || evidence.incomplete) report.tasks[index].status = "incomplete";
    }
    const feedback = failureFeedback(task, report.tasks[index].status, output);
    report.tasks[index].feedback = feedback;
    if (feedback) console.error(`[quality] Next: ${feedback.suggestion} See ${feedback.docs}`);
    report.status = report.tasks.some((entry) => entry.status === "not_run") ? "not_run"
      : report.tasks.every((entry) => entry.status === "passed") ? "passed" : "failed";
    save();
    if (report.tasks[index].status !== "passed") {
      console.error(`[quality] FAILED: ${task.label}${result.error ? `: ${result.error.message}` : ""}`);
      failed = true;
    }
  }
  return Number(failed);
}

export function invocationFor(task, platform = process.platform, npmExecPath = process.env.npm_execpath) {
  if (task.command === "pnpm" && npmExecPath) {
    return /\.[cm]?js$/i.test(npmExecPath)
      ? { command: process.execPath, args: [npmExecPath, ...task.args], shell: false }
      : { command: npmExecPath, args: task.args, shell: false };
  }
  if (task.command === "pnpm" && platform === "win32") {
    // These arguments are fixed in planFor, never filenames or event input.
    // cmd.exe needs explicit quotes to retain the pytest marker expression.
    if (task.args.some((value) => /["&|<>^%!\r\n]/.test(value))) throw new Error("Unsafe package command argument");
    return { command: "pnpm", args: task.args.map((value) => `"${value}"`), shell: true };
  }
  return { ...task, shell: false };
}

export function main(args) {
  const phaseIndex = args.indexOf("--phase");
  const phase = phaseIndex < 0 ? "full" : args[phaseIndex + 1];
  const scopeIndex = args.indexOf("--scope");
  const scope = scopeIndex < 0 ? "all" : args[scopeIndex + 1];
  if (!["quick", "full"].includes(phase) || !["all", "backend", "frontend", "scripts"].includes(scope)) {
    throw new Error("Use --scope all|backend|frontend|scripts and --phase quick|full");
  }
  const scopes = args.includes("--changed") ? scopesFor(changedPaths())
    : scope === "all" ? ["backend", "frontend", "scripts"] : [scope];
  const specIndex = args.indexOf("--spec");
  if (specIndex >= 0 && (!args[specIndex + 1] || args[specIndex + 1].startsWith("--"))) throw new Error("--spec requires a JSON path");
  const specification = loadSpecification(ROOT, specIndex < 0 ? undefined : args[specIndex + 1], phase);
  const plan = buildQualityPlan(scopes, specification, phase, args.includes("--changed"));
  if (args.includes("--list")) {
    console.log(JSON.stringify(plan, null, 2));
    return 0;
  }
  if (!plan.length) console.log("[quality] No code or tooling changes to check.");
  const reportIndex = args.indexOf("--report");
  if (reportIndex >= 0 && !args[reportIndex + 1]) throw new Error("--report requires a path");
  return runPlan(plan, spawnSync, reportIndex >= 0 ? resolve(args[reportIndex + 1]) : null);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { process.exitCode = main(process.argv.slice(2)); }
  catch (error) { console.error(error.message); process.exitCode = 1; }
}
