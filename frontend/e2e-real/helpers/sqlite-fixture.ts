import { spawnSync } from "node:child_process";
import { join } from "node:path";

export interface LogicalSnapshot {
  integrity: string;
  logical_sha256: string;
  journal_mode: string;
  schema: unknown[][];
  tables: Record<string, { columns: string[]; rows: unknown[][] }>;
}

function observe(root: string, mode: string, index: string, env: NodeJS.ProcessEnv) {
  const result = spawnSync(
    join(root, "backend/.venv/Scripts/python.exe"),
    [join(root, "frontend/scripts/sqlite-fixture.py"), mode, index],
    { cwd: root, env, encoding: "utf8", timeout: 120_000, maxBuffer: 32 * 1024 * 1024 },
  );
  if (result.status !== 0) throw new Error(result.stdout + result.stderr);
  return JSON.parse(result.stdout.trim().split("\n").at(-1) || "null");
}

export function restoreHistoricalManifest(
  root: string,
  directory: string,
  env: NodeJS.ProcessEnv,
) {
  const index = join(directory, "historical-manifest.sqlite3");
  observe(root, "restore", index, env);
  return index;
}

export function logicalSnapshot(root: string, index: string): LogicalSnapshot {
  return observe(root, "snapshot", index, process.env);
}

export function assertImportSemantic(root: string, index: string) {
  const result = spawnSync(
    join(root, "backend/.venv/Scripts/python.exe"),
    [
      join(root, "frontend/scripts/semantic-compare.py"),
      "compare",
      join(root, "frontend/e2e-real/fixtures/import-semantic-oracle.json"),
      index,
    ],
    {
      cwd: root,
      env: process.env,
      encoding: "utf8",
      timeout: 120_000,
      maxBuffer: 32 * 1024 * 1024,
    },
  );
  if (result.status !== 0) throw new Error(result.stdout + result.stderr);
  return JSON.parse(result.stdout);
}
