import { existsSync, readFileSync, realpathSync, statSync } from "node:fs";
import { resolve, sep } from "node:path";

export const DEFAULT_SPEC = "tmp/quality/task.json";

const SUITES = {
  postgres: {
    scope: "backend",
    command: "pnpm",
    args: ["test:postgres"],
    testRunner: "pytest",
  },
  browser: {
    scope: "frontend",
    command: "pnpm",
    args: ["test:e2e"],
    testRunner: "playwright",
  },
  "backend-startup": {
    scope: "backend",
    command: "uv",
    args: [
      "run", "--project", "backend", "--locked", "python", "-m",
      "backend.infrastructure.cli.configured_e2e_gate",
    ],
    testRunner: "configured-backend",
  },
};

export function registeredSuite(name) {
  return Object.hasOwn(SUITES, name) ? SUITES[name] : undefined;
}

function fields(value, names) {
  if (!value || typeof value !== "object" || Array.isArray(value)
    || Object.keys(value).some((key) => !names.includes(key))) throw new Error("Invalid quality specification fields");
}

function text(value, name) {
  if (typeof value !== "string" || !value.trim() || value.length > 2000) throw new Error(`Invalid ${name}`);
}

export function specificationPlan(spec, root, phase = "full") {
  fields(spec, ["version", "task", "requirements"]);
  text(spec.task, "task");
  if (spec.version !== 1 || !Array.isArray(spec.requirements) || !spec.requirements.length) throw new Error("Specification requires version 1 and requirements");
  const scopes = new Set();
  const tasks = new Map();
  const ids = new Set();
  for (const requirement of spec.requirements) {
    fields(requirement, ["id", "acceptance", "checks"]);
    text(requirement.id, "requirement id");
    text(requirement.acceptance, "acceptance criterion");
    if (ids.has(requirement.id) || !Array.isArray(requirement.checks) || !requirement.checks.length) throw new Error("Requirements need unique ids and nonempty checks");
    ids.add(requirement.id);
    for (const check of requirement.checks) {
      fields(check, ["kind", "path", "test", "name"]);
      let command, args, layer, testRunner;
      if (check.kind === "suite") {
        const suite = registeredSuite(check.name);
        if (check.path !== undefined || check.test !== undefined || !suite) throw new Error("Unknown integration suite");
        layer = check.name;
        scopes.add(suite.scope);
        if (phase === "quick") continue;
        ({ command, args, testRunner } = suite);
      } else {
        if (check.name !== undefined || typeof check.path !== "string"
          || !/^[a-zA-Z0-9_./-]+$/.test(check.path) || check.path.split("/").some((part) => !part || part === ".." || part === ".")) throw new Error("Unsafe test path");
        const target = resolve(root, check.path);
        if (!existsSync(target) || !statSync(target).isFile() || !realpathSync(target).startsWith(realpathSync(root) + sep)) throw new Error("Test must be an existing file inside the repository");
        const python = check.kind === "python" && /^(backend\/tests|scripts\/hooks)\/.*test[^/]*\.py$/.test(check.path);
        const node = check.kind === "node" && /^(frontend\/(features|shared|scripts)|scripts)\/.*\.test\.mjs$/.test(check.path);
        if (!python && !node) throw new Error("Unsupported test kind or location");
        if (check.test !== undefined && (!python || typeof check.test !== "string" || !/^(test_\w+|Test\w+)(::test_\w+)?$/.test(check.test))) throw new Error("Invalid pytest test selector");
        scopes.add(check.path.startsWith("backend/") ? "backend" : check.path.startsWith("frontend/") ? "frontend" : "scripts");
        layer = "unit";
        command = python ? "uv" : process.execPath;
        testRunner = python ? "pytest" : "node";
        args = python
          ? ["run", "--project", "backend", "--locked", "python", "-m", "pytest", check.path + (check.test ? `::${check.test}` : ""), "-m", "not postgres and not source_data", "-q"]
          : ["--experimental-strip-types", "--test", "--test-timeout=60000", check.path];
      }
      const key = JSON.stringify([command, args]);
      if (!tasks.has(key)) tasks.set(key, { label: `Acceptance: ${check.path ?? check.name}${check.test ? `::${check.test}` : ""}`, command, args, layer, testRunner, requireEvidence: true, specification: spec.task, requirements: [], reasons: [] });
      tasks.get(key).requirements.push(requirement.id);
      tasks.get(key).reasons.push(requirement.acceptance);
    }
  }
  return { task: spec.task, scopes: [...scopes].sort(), tasks: [...tasks.values()] };
}

export function loadSpecification(root, path, phase) {
  const target = resolve(root, path ?? DEFAULT_SPEC);
  if (!existsSync(target) && path === undefined) return { scopes: [], tasks: [] };
  return specificationPlan(JSON.parse(readFileSync(target, "utf8")), root, phase);
}
