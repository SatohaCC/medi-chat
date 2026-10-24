import assert from "node:assert/strict";
import test from "node:test";
import { invocationFor, planFor, runPlan, scopesFor } from "./quality.mjs";

test("documentation changes do not start runtime checks", () => {
  assert.deepEqual(scopesFor(["docs/architecture/backend-design.md", ".agents/guides/backend.md"]), []);
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

test("quick checks include uncached Mypy but omit test suites", () => {
  const labels = planFor(["backend", "frontend"], "quick").map((task) => task.label);
  assert.deepEqual(labels, ["Python lint", "Backend Mypy", "Frontend lint"]);
  const mypy = planFor(["backend"], "quick").find((task) => task.label === "Backend Mypy");
  assert.ok(mypy.args.includes("--no-incremental"));
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
