import { spawnSync } from "node:child_process";
import { join } from "node:path";

export interface LogicalSnapshot {
  integrity: string;
  logical_sha256: string;
  journal_mode: string;
  schema: unknown[][];
  tables: Record<string, { columns: string[]; rows: unknown[][] }>;
}

export function pythonBinary(root: string): string {
  return process.platform === "win32"
    ? join(root, "backend/.venv/Scripts/python.exe")
    : join(root, "backend/.venv/bin/python");
}

function observe(root: string, mode: string, index: string, env: NodeJS.ProcessEnv) {
  const result = spawnSync(
    pythonBinary(root),
    [join(root, "frontend/scripts/sqlite-fixture.py"), mode, index],
    { cwd: root, env, encoding: "utf8", timeout: 120_000, maxBuffer: 32 * 1024 * 1024 },
  );
  if (result.status !== 0) throw new Error(result.stdout + result.stderr);
  return JSON.parse(result.stdout.trim().split("\n").at(-1) || "null");
}

export function logicalSnapshot(root: string, index: string): LogicalSnapshot {
  return observe(root, "snapshot", index, process.env);
}

export function assertCurrentImport(root: string, index: string, directory: string) {
  const result = spawnSync(
    pythonBinary(root),
    [
      join(root, "frontend/scripts/current-import-check.py"),
      join(
        root,
        "data/pmda/originals/イグザレルト錠２．５ｍｇ/630004_3339003F5020_1_08.xml",
      ),
      directory,
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
