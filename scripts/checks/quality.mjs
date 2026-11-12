// Shared, read-only quality entry point for manual runs, CI and Codex hooks.
import { spawn, spawnSync } from "node:child_process";
import { mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { resolve, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { loadSpecification, registeredSuite } from "./quality-spec.mjs";
import { acceptanceEvidence, failureFeedback } from "./quality-feedback.mjs";
import { safeExecuteAsync, safeSpawnSync } from "./safe-process.mjs";

export const ROOT = fileURLToPath(new URL("../../", import.meta.url));
const TEST_RUNTIME_REQUIREMENTS = resolve(ROOT, "scripts/checks/test-runtime-requirements.json");

export function scopesFor(paths) {
  const scopes = new Set();
  for (const path of paths) {
    if (/^(package\.json|pnpm-lock\.yaml|pnpm-workspace\.yaml|\.nvmrc|\.python-version|pyrightconfig\.json)$/.test(path) || path.startsWith(".github/")) {
      for (const scope of ["backend", "frontend", "scripts"]) scopes.add(scope);
    }
    if (path.startsWith("backend/")) scopes.add("backend");
    if (path === "pytest.ini" || path === "conftest.py") {
      scopes.add("backend");
      scopes.add("scripts");
    }
    if (path.startsWith("frontend/")) scopes.add("frontend");
    if (path.startsWith("scripts/") || path.startsWith(".codex/") || path.startsWith(".agents/")) scopes.add("scripts");
    if (path.startsWith("scripts/checks/") || path.startsWith("scripts/hooks/") || path.startsWith(".agents/")) scopes.add("backend");
  }
  return [...scopes].sort();
}

export function requireSpecificationForScope(required, scopes) {
  return Boolean(required && scopes.length > 0);
}

function nodeTests(folder, root = ROOT) {
  return readdirSync(resolve(root, folder), { recursive: true, withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith(".test.mjs"))
    .map((entry) => relative(root, resolve(entry.parentPath, entry.name)).replaceAll("\\", "/"))
    .sort();
}

export function findUnregisteredPythonBridgeTests(tests, requirements, readSource) {
  return tests.filter((path) => {
    const source = readSource(path);
    const startsPythonProcess = /\b(?:execFileSync|execFile|spawnSync|spawn|execSync)\s*\(/.test(source);
    const namesPythonRuntime = /["'`](?:uv|python(?:3)?(?:\.exe)?)["'`]/.test(source);
    return startsPythonProcess && namesPythonRuntime && !requirements.tests[path]?.includes("python");
  });
}

export function partitionNodeTests(tests, requirements, readSource = () => "") {
  if (requirements.version !== 1 || !requirements.tests || typeof requirements.tests !== "object") {
    throw new Error("Invalid test runtime requirements manifest");
  }
  const knownTests = new Set(tests);
  const unknown = Object.keys(requirements.tests).filter((path) => !knownTests.has(path));
  if (unknown.length) throw new Error(`Runtime requirements reference unknown tests: ${unknown.join(", ")}`);
  for (const [path, runtimes] of Object.entries(requirements.tests)) {
    if (!Array.isArray(runtimes) || runtimes.length !== 2 || runtimes[0] !== "node" || runtimes[1] !== "python") {
      throw new Error(`Invalid runtimes for ${path}; expected ["node", "python"]`);
    }
  }
  const unregistered = findUnregisteredPythonBridgeTests(tests, requirements, readSource);
  if (unregistered.length) throw new Error(`Python-backed tests need runtime metadata: ${unregistered.join(", ")}`);
  const pythonTests = tests.filter((path) => requirements.tests[path]?.includes("python"));
  const pythonSet = new Set(pythonTests);
  return {
    node: tests.filter((path) => !pythonSet.has(path)),
    python: pythonTests,
  };
}

export function nodeTestGroups(scopes, root = ROOT) {
  const directories = scopes.includes("frontend")
    ? ["frontend/features", "frontend/shared", "frontend/scripts"]
    : [];
  const tests = directories.flatMap((folder) => nodeTests(folder, root));
  const requirements = JSON.parse(readFileSync(resolve(root, "scripts/checks/test-runtime-requirements.json"), "utf8"));
  return partitionNodeTests(tests, requirements, (path) => readFileSync(resolve(root, path), "utf8"));
}

export function planFor(scopes, phase = "full", { includeBackendStartup = false } = {}) {
  const plan = [];
  const pnpm = (label, ...args) => plan.push({ label, command: "pnpm", args });
  const uv = (label, ...args) => plan.push({ label, command: "uv", args: ["run", "--project", "backend", "--locked", ...args] });
  const node = (label, args, options = {}) => plan.push({ label, command: process.execPath, args, ...options });
  if (scopes.includes("backend")) {
    if (phase === "quick") {
      uv("Python lint", "ruff", "check", "backend", "scripts/checks", "scripts/hooks");
      uv("Backend Mypy", "mypy", "--config-file", "backend/pyproject.toml", "-p", "backend");
      uv("Layer boundaries", "python", "scripts/checks/layer_architecture.py");
      uv("Domain architecture", "python", "scripts/checks/domain_architecture.py");
      uv("Application architecture", "python", "scripts/checks/application_architecture.py");
      uv("Infrastructure architecture", "python", "scripts/checks/infrastructure_architecture.py");
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
    node("Frontend boundaries", ["frontend/scripts/shared-boundaries.mjs"]);
    if (phase === "full") {
      pnpm("Frontend format", "--filter", "frontend", "exec", "biome", "format", ".");
      pnpm("StyleX lint", "--filter", "frontend", "lint:stylex");
      pnpm("Frontend types", "typecheck:frontend");
      const tests = nodeTestGroups(scopes);
      node("Frontend Node unit tests", ["scripts/checks/run-node-tests.mjs", ...tests.node]);
      if (tests.python.length) {
        node("Frontend Node tests requiring Python", ["scripts/checks/run-node-tests.mjs", ...tests.python], { runtimes: ["node", "python"] });
      }
    }
  }
  if (scopes.includes("scripts")) {
    uv("Root pytest lint", "ruff", "check", "--config", "backend/pyproject.toml", "conftest.py");
    uv("Root pytest Mypy", "mypy", "--config-file", "backend/pyproject.toml", "conftest.py");
    pnpm("Root pytest Pyright", "exec", "pyright", "conftest.py");
    if (phase === "full") {
      uv("Root pytest format", "ruff", "format", "--check", "--config", "backend/pyproject.toml", "conftest.py");
      node("Development tooling tests", ["scripts/checks/run-node-tests.mjs", ...nodeTests("scripts")]);
      node("Source-data dependency guard", ["scripts/checks/source-data-guard.mjs", "--check"]);
    }
    else node("Quality runner syntax", ["--check", "scripts/checks/quality.mjs"]);
    uv("Tooling lint", "ruff", "check", "scripts/checks", "scripts/hooks");
    if (phase === "full") {
      uv("Tooling format", "ruff", "format", "--check", "scripts/checks", "scripts/hooks");
      pnpm("Tooling types (Pyright and mypy)", "typecheck:scripts");
      uv("Hook regression tests", "python", "-m", "pytest", "scripts/hooks/test_quality_gate.py", "scripts/hooks/test_privacy_gate.py", "scripts/hooks/test_quality_ci_contract.py", "scripts/hooks/test_antigravity_adapter.py", "-q");
      pnpm("Generated requirements", "vercel:requirements:check");
      uv("Generated search guide", "python", "-m", "backend.infrastructure.cli.export_search_guide", "--check");
    }
  }
  return plan;
}

export function buildQualityPlan(scopes, specification, phase = "full", changed = false) {
  const combinedScopes = [...new Set([...scopes, ...specification.scopes])];
  const explicitlySelectedStartup = specification.tasks.some(
    (task) => task.layer === "backend-startup" || task.layer === "browser"
  );
  const includeBackendStartup = changed
    && phase === "full"
    && combinedScopes.includes("backend")
    && !explicitlySelectedStartup;
  return [
    ...specification.tasks,
    ...planFor(combinedScopes, phase, { includeBackendStartup }),
  ];
}

export function taskResource(task) {
  if (task.resource) return task.resource;
  if (task.layer === "backend-startup" || task.layer === "browser") return "configured-backend-probe";
  if (task.command === "uv" || task.runtimes?.includes("python")) return "uv-python-env";
  return null;
}

export function changedPaths(root = ROOT) {
  const collect = (args) => {
    const result = safeSpawnSync("git", args, { cwd: root, encoding: "utf8" });
    if (result.status !== 0) throw new Error(result.stderr || "Cannot inspect Git changes");
    return result.stdout.split("\0").filter(Boolean);
  };
  return [...new Set([
    ...collect(["diff", "HEAD", "--name-only", "-z", "--no-renames"]),
    ...collect(["ls-files", "--others", "--exclude-standard", "-z"]),
  ])].sort();
}

export function executeAsync(command, args, options = {}) {
  return safeExecuteAsync(command, args, options);
}

function recordTaskResult(report, index, task, result, started, save) {
  Object.assign(report.tasks[index], {
    status: result.error?.code === "ETIMEDOUT" ? "timeout"
      : result.error ? "start_error" : result.status === 0 ? "passed" : "failed",
    exitCode: result.status ?? null,
    durationMs: Date.now() - started,
  });
  const output = `${result.stdout ?? ""}\n${result.stderr ?? ""}`;
  if (task.requireEvidence && report.tasks[index].status === "passed") {
    const evidence = acceptanceEvidence(output, task.testRunner, task.selectors);
    report.tasks[index].evidence = evidence;
    if (!evidence.passed || evidence.incomplete) report.tasks[index].status = "incomplete";
  }
  const feedback = failureFeedback(task, report.tasks[index].status, output, report.tasks[index].exitCode);
  report.tasks[index].feedback = feedback;

  console.log(`\n[quality] ${task.label}`);
  if (result.stdout) process.stdout.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);
  if (feedback) console.error(`[quality] Next: ${feedback.suggestion} See ${feedback.docs}`);
  if (report.tasks[index].status !== "passed") {
    console.error(`[quality] FAILED: ${task.label}${result.error ? `: ${result.error.message}` : ""}`);
  }

  const hasFailed = report.tasks.some((entry) => ["failed", "incomplete", "timeout", "start_error"].includes(entry.status));
  const hasPending = report.tasks.some((entry) => entry.status === "not_run");
  report.status = hasFailed ? "failed" : hasPending ? "not_run" : "passed";
  save();

  return report.tasks[index].status !== "passed";
}

export function runPlan(plan, execute = safeSpawnSync, reportPath = null, { concurrency = 1 } = {}) {
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
  const execOptions = {
    cwd: ROOT,
    stdio: "pipe",
    encoding: "utf8",
    maxBuffer: 16 * 1024 * 1024,
    timeout: 300_000,
    env: {
      ...process.env,
      UV_CACHE_DIR: process.env.UV_CACHE_DIR?.trim() || resolve(ROOT, ".uv-cache"),
      PYTHONUTF8: "1",
      PYTHONIOENCODING: "utf-8",
      TMP: temporary,
      TEMP: temporary,
      TMPDIR: temporary,
    },
  };

  if (concurrency > 1 || (execute && (execute === executeAsync || execute.constructor?.name === "AsyncFunction"))) {
    return (async () => {
      const completed = new Set();
      const inProgress = new Set();
      const activeResources = new Set();
      const waiters = new Set();

      function getNextTaskIndex() {
        for (let i = 0; i < plan.length; i++) {
          if (completed.has(i) || inProgress.has(i)) continue;
          const resource = taskResource(plan[i]);
          if (resource && activeResources.has(resource)) continue;
          inProgress.add(i);
          if (resource) activeResources.add(resource);
          return i;
        }
        return -1;
      }

      function notifyWaiters() {
        for (const wake of waiters) wake();
        waiters.clear();
      }

      async function worker() {
        while (completed.size < plan.length) {
          const index = getNextTaskIndex();
          if (index === -1) {
            if (completed.size === plan.length) break;
            await new Promise((wake) => waiters.add(wake));
            continue;
          }
          const task = plan[index];
          const started = Date.now();
          let result;
          if (task.specError) {
            result = { status: 1, error: null, stdout: "", stderr: `${task.specError}\n` };
          } else {
            const invocation = invocationFor(task);
            result = await execute(invocation.command, invocation.args, {
              ...execOptions,
              shell: invocation.shell,
            });
          }
          if (recordTaskResult(report, index, task, result, started, save)) failed = true;
          const resource = taskResource(task);
          if (resource) activeResources.delete(resource);
          inProgress.delete(index);
          completed.add(index);
          notifyWaiters();
        }
      }
      const workers = Array.from(
        { length: Math.min(concurrency, Math.max(1, plan.length)) },
        () => worker()
      );
      await Promise.all(workers);
      return Number(failed);
    })();
  }

  for (const [index, task] of plan.entries()) {
    const started = Date.now();
    let result;
    if (task.specError) {
      result = { status: 1, error: null, stdout: "", stderr: `${task.specError}\n` };
    } else {
      const invocation = invocationFor(task);
      result = execute(invocation.command, invocation.args, {
        ...execOptions,
        shell: invocation.shell,
      });
    }
    if (recordTaskResult(report, index, task, result, started, save)) failed = true;
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

export async function main(args) {
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
  const reportIndex = args.indexOf("--report");
  if (reportIndex >= 0 && (!args[reportIndex + 1] || args[reportIndex + 1].startsWith("--"))) throw new Error("--report requires a path");
  let specification;
  try {
    specification = loadSpecification(
      ROOT,
      specIndex < 0 ? undefined : args[specIndex + 1],
      phase,
      requireSpecificationForScope(args.includes("--require-spec"), scopes),
    );
  } catch (error) {
    if (args.includes("--list")) throw error;
    specification = {
      scopes: [],
      tasks: [{ label: "Quality specification", command: process.execPath, args: [], specError: error.message }],
    };
  }
  const plan = buildQualityPlan(scopes, specification, phase, args.includes("--changed"));
  if (args.includes("--list")) {
    console.log(JSON.stringify(plan, null, 2));
    return 0;
  }
  if (!plan.length) console.log("[quality] No code or tooling changes to check.");

  const concurrencyIndex = args.indexOf("--concurrency");
  const concurrency = args.includes("--serial")
    ? 1
    : concurrencyIndex >= 0
      ? parseInt(args[concurrencyIndex + 1], 10)
      : (args.includes("--parallel") || phase === "full" ? 4 : 1);
  const executor = concurrency > 1 ? executeAsync : safeSpawnSync;
  return await runPlan(plan, executor, reportIndex >= 0 ? resolve(args[reportIndex + 1]) : null, { concurrency });
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { process.exitCode = await main(process.argv.slice(2)); }
  catch (error) { console.error(error.message); process.exitCode = 1; }
}
