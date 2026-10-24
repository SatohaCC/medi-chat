// Shared, read-only quality entry point for manual runs, CI and Codex hooks.
import { spawnSync } from "node:child_process";
import { mkdirSync, readdirSync } from "node:fs";
import { resolve, relative } from "node:path";
import { fileURLToPath } from "node:url";

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

export function planFor(scopes, phase = "full") {
  const plan = [];
  const pnpm = (label, ...args) => plan.push({ label, command: "pnpm", args });
  const uv = (label, ...args) => plan.push({ label, command: "uv", args: ["run", "--project", "backend", "--locked", ...args] });
  const node = (label, args) => plan.push({ label, command: process.execPath, args });
  if (scopes.includes("backend")) {
    if (phase === "quick") {
      uv("Python lint", "ruff", "check", "backend", "scripts/checks", "scripts/hooks");
      uv("Backend Mypy", "mypy", "--config-file", "backend/pyproject.toml", "--no-incremental", "-p", "backend");
    } else {
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
      uv("Hook regression tests", "python", "-m", "pytest", "scripts/hooks/test_quality_gate.py", "-q");
      pnpm("Generated requirements", "vercel:requirements:check");
      uv("Generated search guide", "python", "-m", "backend.infrastructure.cli.export_search_guide", "--check");
    }
  }
  return plan;
}

export function changedPaths() {
  const collect = (args) => {
    const result = spawnSync("git", args, { cwd: ROOT, encoding: "utf8" });
    if (result.status !== 0) throw new Error(result.stderr || "Cannot inspect Git changes");
    return result.stdout.split("\0").filter(Boolean);
  };
  return [...new Set([
    ...collect(["diff", "HEAD", "--name-only", "-z", "--no-renames"]),
    ...collect(["ls-files", "--others", "--exclude-standard", "-z"]),
  ])].sort();
}

export function runPlan(plan, execute = spawnSync) {
  let failed = false;
  const temporary = resolve(ROOT, "tmp/quality");
  mkdirSync(temporary, { recursive: true });
  for (const task of plan) {
    console.log(`\n[quality] ${task.label}`);
    const invocation = invocationFor(task);
    const result = execute(invocation.command, invocation.args, {
      cwd: ROOT,
      stdio: "inherit",
      shell: invocation.shell,
      timeout: 300_000,
      env: { ...process.env, UV_CACHE_DIR: resolve(ROOT, ".uv-cache"), TMP: temporary, TEMP: temporary, TMPDIR: temporary },
    });
    if (result.error || result.status !== 0) {
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
  const plan = planFor(scopes, phase);
  if (args.includes("--list")) {
    console.log(JSON.stringify(plan, null, 2));
    return 0;
  }
  if (!plan.length) console.log("[quality] No code or tooling changes to check.");
  return runPlan(plan);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { process.exitCode = main(process.argv.slice(2)); }
  catch (error) { console.error(error.message); process.exitCode = 1; }
}
