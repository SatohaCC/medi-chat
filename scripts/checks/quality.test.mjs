import assert from "node:assert/strict";
import test from "node:test";
import { mkdtempSync, readFileSync, writeFileSync, mkdirSync, renameSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { execFileSync } from "node:child_process";
import { buildQualityPlan, changedPaths, invocationFor, planFor, runPlan, scopesFor } from "./quality.mjs";

test("reports distinguish failure, timeout, launch error and unexecuted work", () => {
  const folder = mkdtempSync(join(tmpdir(), "quality-report-"));
  try {
    const reportPath = join(folder, "report.json");
    const plan = ["success", "failure", "timeout", "missing"].map((label) => ({ label, command: process.execPath, args: [] }));
    const outcomes = [
      { status: 0 }, { status: 2 },
      { status: null, error: Object.assign(new Error("timeout"), { code: "ETIMEDOUT" }) },
      { status: null, error: Object.assign(new Error("missing"), { code: "ENOENT" }) },
    ];
    let index = 0;
    assert.equal(runPlan(plan, () => {
      const current = JSON.parse(readFileSync(reportPath, "utf8"));
      assert.equal(current.tasks[index].status, "not_run");
      assert.notEqual(current.status, "passed");
      return outcomes[index++];
    }, reportPath), 1);
    const report = JSON.parse(readFileSync(reportPath, "utf8"));
    assert.deepEqual(report.tasks.map((task) => task.status), ["passed", "failed", "timeout", "start_error"]);
    assert.equal(report.status, "failed");
    assert.equal(report.tasks[1].exitCode, 2);
    assert.deepEqual(report.excludedLayers, ["backend-startup", "postgres", "browser", "external_api"]);
    assert.equal(runPlan([], undefined, reportPath), 0);
    assert.equal(JSON.parse(readFileSync(reportPath, "utf8")).status, "not_run");
  } finally {
    rmSync(folder, { recursive: true, force: true });
  }
});

test("real Git changes retain both sides of renames and shared settings select all scopes", () => {
  const folder = mkdtempSync(join(tmpdir(), "quality-git-"));
  const git = (...args) => execFileSync("git", args, { cwd: folder, stdio: "pipe" });
  try {
    git("init");
    mkdirSync(join(folder, "backend"));
    writeFileSync(join(folder, "backend/old.py"), "fixture");
    writeFileSync(join(folder, "pnpm-lock.yaml"), "before");
    git("add", ".");
    git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "--no-verify", "-m", "fixture");
    mkdirSync(join(folder, "scripts"));
    renameSync(join(folder, "backend/old.py"), join(folder, "scripts/new.py"));
    git("add", ".");
    writeFileSync(join(folder, "pnpm-lock.yaml"), "after");
    writeFileSync(join(folder, "backend/untracked.py"), "new");
    assert.deepEqual(changedPaths(folder), ["backend/old.py", "backend/untracked.py", "pnpm-lock.yaml", "scripts/new.py"]);
    assert.deepEqual(scopesFor(changedPaths(folder)), ["backend", "frontend", "scripts"]);
  } finally {
    rmSync(folder, { recursive: true, force: true });
  }
});

test("every existing frontend and tooling Node test is included in the full plan", () => {
  const tracked = execFileSync("git", ["ls-files", "-z"], { encoding: "utf8" }).split("\0");
  const planned = new Set(planFor(["frontend", "scripts"]).flatMap((task) => task.args));
  for (const path of tracked.filter((path) => /^(frontend|scripts)\/.*\.test\.mjs$/.test(path))) {
    assert.ok(planned.has(path), `Node test is outside the quality plan: ${path}`);
  }
});

test("CI retains the shared backend and tooling gates plus the separate PostgreSQL gate", () => {
  const workflow = readFileSync(new URL("../../.github/workflows/postgres-contracts.yml", import.meta.url), "utf8");
  for (const command of ["pnpm quality:backend", "pnpm quality:scripts", "pnpm test:postgres"]) {
    assert.ok(workflow.includes(`run: ${command}`), `Missing CI gate: ${command}`);
  }
});

test("documentation changes do not start runtime checks", () => {
  assert.deepEqual(scopesFor(["docs/architecture/backend-design.md", "AGENTS.md"]), []);
});

test("staged/deleted/backend and shared configuration select affected scopes", () => {
  assert.deepEqual(scopesFor(["backend/deleted.py"]), ["backend"]);
  assert.deepEqual(scopesFor(["pytest.ini"]), ["backend", "scripts"]);
  assert.deepEqual(scopesFor(["scripts/checks/domain_architecture.py"]), ["backend", "scripts"]);
  assert.deepEqual(scopesFor(["pnpm-lock.yaml"]), ["backend", "frontend", "scripts"]);
});

test("full checks include tests, types and architecture without DB/browser commands", () => {
  const plan = planFor(["backend", "frontend", "scripts"]);
  const commands = plan.map((task) => task.args.join(" ")).join("\n");
  assert.match(commands, /--filter backend lint/);
  assert.match(commands, /typecheck:python/);
  assert.match(commands, /typecheck:frontend/);
  assert.match(commands, /test:backend -m not source_data/);
  assert.match(commands, /chatWebSocket.test.mjs/);
  assert.match(commands, /test_quality_gate.py/);
  assert.doesNotMatch(commands, /test:postgres|test:e2e|--write|--fix/);
});

test("backend startup runs automatically in changed full checks, not quick or package-only plans", () => {
  const noSpecification = { scopes: [], tasks: [] };
  const normalFull = buildQualityPlan(["backend"], noSpecification, "full", false);
  const changedFull = buildQualityPlan(["backend"], noSpecification, "full", true);
  const changedQuick = buildQualityPlan(["backend"], noSpecification, "quick", true);
  const startupTasks = changedFull.filter((task) => task.layer === "backend-startup");

  assert.equal(normalFull.some((task) => task.layer === "backend-startup"), false);
  assert.equal(startupTasks.length, 1);
  assert.deepEqual(startupTasks[0].args, [
    "run", "--project", "backend", "--locked", "python", "-m",
    "backend.infrastructure.cli.configured_e2e_gate",
  ]);
  assert.equal(startupTasks[0].requireEvidence, true);
  assert.equal(changedQuick.some((task) => task.layer === "backend-startup"), false);

  const explicitStartup = {
    scopes: ["backend"],
    tasks: [{ ...startupTasks[0], label: "Acceptance: backend-startup" }],
  };
  const noDuplicate = buildQualityPlan(["backend"], explicitStartup, "full", true);
  assert.equal(noDuplicate.filter((task) => task.layer === "backend-startup").length, 1);
});

test("quick checks include cached Backend Mypy but omit test suites", () => {
  const labels = planFor(["backend", "frontend"], "quick").map((task) => task.label);
  assert.deepEqual(labels, ["Python lint", "Backend Mypy", "Frontend lint"]);
  const mypy = planFor(["backend"], "quick").find((task) => task.label === "Backend Mypy");
  assert.ok(!mypy.args.includes("--no-incremental"));
  assert.deepEqual(mypy.args.slice(-2), ["-p", "backend"]);
});

test("scripts-only changes run tooling type checks in the full gate", () => {
  const plan = planFor(scopesFor(["scripts/hooks/quality_gate.py"]));
  assert.ok(plan.some((task) => task.command === "pnpm" && task.args[0] === "typecheck:scripts"));
  const scriptsOnly = planFor(["scripts"]);
  assert.ok(scriptsOnly.some((task) => task.command === "pnpm" && task.args[0] === "typecheck:scripts"));
});

test("package manager forwarding preserves a pytest expression as one argument", () => {
  const task = { command: "pnpm", args: ["test:backend", "-m", "not source_data"] };
  const direct = invocationFor(task, "win32", "C:/Program Files/pnpm/pnpm.cjs");
  assert.equal(direct.shell, false);
  assert.equal(direct.args.at(-1), "not source_data");
  const native = invocationFor(task, "win32", "C:/pnpm/pnpm-native.exe");
  assert.equal(native.command, "C:/pnpm/pnpm-native.exe");
  assert.equal(native.args.at(-1), "not source_data");
  assert.equal(native.shell, false);
  const fallback = invocationFor(task, "win32", "");
  assert.equal(fallback.args.at(-1), '"not source_data"');
});

test("failed or unstarted commands fail the gate and remaining checks still run", () => {
  const plan = [{ label: "one", command: "node", args: [] }, { label: "two", command: "node", args: [] }];
  let calls = 0;
  assert.equal(runPlan(plan, () => ({ status: ++calls === 1 ? 1 : 0 })), 1);
  assert.equal(calls, 2);
  assert.equal(runPlan(plan, () => ({ status: null, error: new Error("missing executable") })), 1);
});

test("runPlan executes tasks concurrently with concurrency > 1", async () => {
  const folder = mkdtempSync(join(tmpdir(), "quality-parallel-"));
  try {
    const reportPath = join(folder, "report.json");
    let active = 0;
    let maxActive = 0;
    const plan = [1, 2, 3, 4].map((n) => ({ label: `task-${n}`, command: "test", args: [] }));
    const mockExecute = async () => {
      active++;
      maxActive = Math.max(maxActive, active);
      await new Promise((r) => setTimeout(r, 40));
      active--;
      return { status: 0, stdout: "ok\n" };
    };
    const exitCode = await runPlan(plan, mockExecute, reportPath, { concurrency: 2 });
    assert.equal(exitCode, 0);
    assert.ok(maxActive >= 2, `Expected concurrency >= 2, got ${maxActive}`);
    const report = JSON.parse(readFileSync(reportPath, "utf8"));
    assert.equal(report.status, "passed");
    assert.equal(report.tasks.length, 4);
    assert.equal(report.tasks.every((t) => t.status === "passed"), true);
  } finally {
    rmSync(folder, { recursive: true, force: true });
  }
});
