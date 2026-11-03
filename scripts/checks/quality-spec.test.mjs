import assert from "node:assert/strict";
import test from "node:test";
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { specificationPlan, loadSpecification } from "./quality-spec.mjs";
import { acceptanceEvidence, failureFeedback } from "./quality-feedback.mjs";
import { runPlan } from "./quality.mjs";

function fixture(run) {
  const root = mkdtempSync(join(tmpdir(), "quality-spec-"));
  mkdirSync(join(root, "backend/tests"), { recursive: true });
  writeFileSync(join(root, "backend/tests/test_contract.py"), "# fixture");
  const check = { kind: "python", path: "backend/tests/test_contract.py", test: "test_contract" };
  const spec = { version: 1, task: "contract", requirements: [{ id: "R1", acceptance: "reject unauthorized access", checks: [check] }] };
  try { run(root, spec, check); } finally { rmSync(root, { recursive: true, force: true }); }
}

test("acceptance criteria select tests even without matching changed paths and preserve reasons", () => fixture((root, spec) => {
  spec.requirements.push({ ...spec.requirements[0], id: "R2", acceptance: "fail closed" });
  const plan = specificationPlan(spec, root);
  assert.deepEqual(plan.scopes, ["backend"]);
  assert.equal(plan.tasks.length, 1);
  assert.deepEqual(plan.tasks[0].requirements, ["R1", "R2"]);
  assert.deepEqual(plan.tasks[0].reasons, ["reject unauthorized access", "fail closed"]);
  assert.ok(plan.tasks[0].args.includes("backend/tests/test_contract.py::test_contract"));
}));

test("missing requirements, unknown commands, unsafe paths and nonexistent tests fail closed", () => fixture((root, spec, check) => {
  for (const mutation of [
    () => ({ ...spec, requirements: [] }),
    () => ({ ...spec, command: "anything" }),
    () => ({ ...spec, requirements: [{ ...spec.requirements[0], checks: [] }] }),
    ...["../outside.py", "/backend/tests/test_contract.py", "backend/tests/../tests/test_contract.py", "backend/tests/missing.py", "backend/tests/test_contract.py;echo"].map((path) => () => ({ ...spec, requirements: [{ ...spec.requirements[0], checks: [{ ...check, path }] }] })),
  ]) assert.throws(() => specificationPlan(mutation(), root));
  assert.throws(() => loadSpecification(root, "missing.json"));
  assert.deepEqual(loadSpecification(root), { scopes: [], tasks: [] });
}));

test("integration layers require an explicit specification and use only registered commands", () => fixture((root, spec) => {
  spec.requirements[0].checks = [
    { kind: "suite", name: "postgres" },
    { kind: "suite", name: "browser" },
    { kind: "suite", name: "backend-startup" },
  ];
  const plan = specificationPlan(spec, root);
  assert.deepEqual(plan.tasks.map((task) => task.args), [
    ["test:postgres"],
    ["test:e2e"],
    ["run", "--project", "backend", "--locked", "python", "-m", "backend.infrastructure.cli.configured_e2e_gate"],
  ]);
  assert.deepEqual(plan.tasks.map((task) => task.testRunner), ["pytest", "playwright", "configured-backend"]);
  assert.deepEqual(plan.scopes, ["backend", "frontend"]);
  assert.deepEqual(specificationPlan(spec, root, "quick").tasks, []);
  spec.requirements[0].checks = [{ kind: "suite", name: "shell" }];
  assert.throws(() => specificationPlan(spec, root));
}));

test("configured backend evidence requires both PostgreSQL readiness and OS health", () => {
  const successful = [
    JSON.stringify({ backend: "postgresql" }),
    JSON.stringify({ backend: "postgresql", readiness: "passed", os_health: { status: "ok" } }),
  ].join("\n");
  assert.deepEqual(acceptanceEvidence(successful, "configured-backend"), { passed: 1, incomplete: false });
  for (const output of [
    JSON.stringify({ backend: "postgresql", readiness: "passed" }),
    JSON.stringify({ backend: "postgresql", readiness: "failed", os_health: { status: "ok" } }),
    "Configured gate failed: schema_not_ready",
  ]) {
    assert.deepEqual(acceptanceEvidence(output, "configured-backend"), { passed: 0, incomplete: true });
  }
});

test("selected backend startup suite records a configured gate failure in the report", () => fixture((root, spec) => {
  spec.requirements[0].checks = [{ kind: "suite", name: "backend-startup" }];
  const task = specificationPlan(spec, root).tasks[0];
  const reportPath = join(tmpdir(), "quality-startup-" + process.pid + "-" + Date.now() + ".json");
  try {
    assert.equal(runPlan([task], () => ({
      status: 1,
      stdout: "Configured gate failed: schema_not_ready",
      stderr: "",
    }), reportPath), 1);
    const report = JSON.parse(readFileSync(reportPath, "utf8"));
    assert.equal(report.status, "failed");
    assert.equal(report.tasks[0].status, "failed");
    assert.deepEqual(report.tasks[0].requirements, ["R1"]);
  } finally {
    rmSync(reportPath, { force: true });
  }
}));

test("feedback retains stable failure identity across line shifts and distinguishes different failing tests", () => {
  const task = { label: "Acceptance contract", requirements: ["R1"] };
  const a = failureFeedback(task, "failed", "FAILED backend/tests/test_contract.py::test_access - AssertionError\n1 failed in 1.2s");
  const b = failureFeedback(task, "failed", "FAILED backend/tests/test_contract.py::test_access - AssertionError\n1 failed in 9.5s");
  const c = failureFeedback(task, "failed", "FAILED backend/tests/test_contract.py::test_other - AssertionError");
  assert.equal(a.identity, b.identity);
  assert.notEqual(a.identity, c.identity);
  const typeTask = { label: "Backend Mypy" };
  assert.equal(failureFeedback(typeTask, "failed", "a.py:12: error: bad type [arg-type]").identity,
    failureFeedback(typeTask, "failed", "a.py:99: error: bad type [arg-type]").identity);
  assert.match(a.suggestion, /受入条件/);
  assert.match(failureFeedback(task, "failed", "PermissionError: denied").suggestion, /通常の承認経路/);
  assert.match(failureFeedback(task, "timeout").suggestion, /待ち条件/);
  assert.equal(failureFeedback(task, "failed", "unknown failure").identity, null);
  assert.notEqual(failureFeedback(task, "failed", "  ✖ parent\n    ✖ child A").identity,
    failureFeedback(task, "failed", "  ✖ parent\n    ✖ child B").identity);
  assert.notEqual(failureFeedback(task, "failed", "✖ same test\n  TypeError: missing value").identity,
    failureFeedback(task, "failed", "✖ same test\n  AssertionError: wrong value").identity);
  const lint = failureFeedback({ label: "Python lint" }, "failed", "F401 [*] `os` imported but unused\n --> a.py:12:1\n");
  assert.ok(lint.identity);
  assert.match(lint.suggestion, /未使用importを削除/);
});

test("a real failing Node test yields a diagnostic and repair advice in the report", () => {
  const root = mkdtempSync(join(tmpdir(), "quality-failure-"));
  try {
    const path = join(root, "contract.test.mjs");
    const report = join(root, "report.json");
    writeFileSync(path, "import test from 'node:test'; import assert from 'node:assert/strict'; test('rejects invalid input', () => assert.equal(1, 2));");
    const execute = (command, args, options) => {
      const env = { ...options.env };
      delete env.NODE_TEST_CONTEXT;
      return spawnSync(command, args, { ...options, env });
    };
    assert.equal(runPlan([{ label: "Acceptance fixture", command: process.execPath, args: ["--test", path], requirements: ["R1"] }], execute, report), 1);
    const feedback = JSON.parse(readFileSync(report, "utf8")).tasks[0].feedback;
    assert.ok(feedback.identity);
    assert.ok(feedback.diagnostics.some((diagnostic) => diagnostic.includes("rejects invalid input")));
    assert.deepEqual(feedback.requirements, ["R1"]);
    assert.match(feedback.suggestion, /受入条件/);
  } finally { rmSync(root, { recursive: true, force: true }); }
});

test("zero tests and skipped acceptance criteria never certify a requirement", () => {
  for (const output of ["0 passed", "ℹ pass 0\nℹ skipped 1", "1 skipped", "1 passed, 1 xfailed", "unknown output"]) {
    const evidence = acceptanceEvidence(output);
    assert.ok(!evidence.passed || evidence.incomplete, output);
    assert.equal(runPlan([{ label: "Acceptance", command: process.execPath, args: [], requireEvidence: true }], () => ({ status: 0, stdout: output })), 1);
  }
  assert.deepEqual(acceptanceEvidence("1 passed, 12 deselected"), { passed: 1, incomplete: false });
  assert.deepEqual(acceptanceEvidence("ℹ pass 3\nℹ skipped 0"), { passed: 3, incomplete: false });
  assert.deepEqual(acceptanceEvidence("1 skipped\nℹ tests 3\nℹ pass 3\nℹ skipped 0"), { passed: 3, incomplete: false });
});

test("browser evidence preserves skipped counts on separate lines and in earlier required layers", () => {
  assert.deepEqual(acceptanceEvidence("  1 skipped\n  2 passed (1.2s)", "playwright"), { passed: 2, incomplete: true });
  assert.deepEqual(acceptanceEvidence("mock suite\n  1 skipped\n  2 passed (1.2s)\nreal suite\n  3 passed (2.0s)", "playwright"), { passed: 5, incomplete: true });
  assert.deepEqual(acceptanceEvidence("mock suite\n  2 passed (1.2s)\nreal suite\n  3 passed (2.0s)", "playwright"), { passed: 5, incomplete: false });
  assert.deepEqual(acceptanceEvidence("ℹ tests 1\nℹ pass 1\nℹ skipped 0\n  1 skipped\n  2 passed (1.2s)", "playwright"), { passed: 2, incomplete: true });
  assert.deepEqual(acceptanceEvidence("ℹ tests 1\nℹ pass 1\nℹ skipped 0", "playwright"), { passed: 0, incomplete: false });
  assert.equal(runPlan([{ label: "Browser acceptance", command: "pnpm", args: ["test:e2e"], requireEvidence: true, testRunner: "playwright" }], () => ({ status: 0, stdout: "  1 skipped\n  2 passed (1.2s)" })), 1);
});
