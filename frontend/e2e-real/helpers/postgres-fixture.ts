import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join } from "node:path";

export interface LogicalSnapshot {
  integrity: string;
  logical_sha256: string;
  tables: Record<string, { columns: string[]; rows: unknown[][] }>;
}

export function pythonBinary(root: string): string {
  return process.platform === "win32"
    ? join(root, "backend/.venv/Scripts/python.exe")
    : join(root, "backend/.venv/bin/python");
}

function command(root: string, args: string[]) {
  const result = spawnSync(pythonBinary(root), args, {
    cwd: root, env: { ...process.env, PYTHONUTF8: "1" }, encoding: "utf8",
    timeout: 120_000, maxBuffer: 32 * 1024 * 1024,
  });
  if (result.status !== 0) throw new Error(result.stdout + result.stderr);
  return JSON.parse(result.stdout.trim().split("\n").at(-1) || "null");
}

export function logicalSnapshot(root: string, fixture: string): LogicalSnapshot {
  return command(root, ["-m", "backend.tests.support.postgres_browser_fixture", "snapshot", "--root", fixture]);
}

export function cleanupFixture(root: string, fixture: string) {
  if (!existsSync(join(fixture, "postgres-fixture.json"))) return;
  command(root, ["-m", "backend.tests.support.postgres_browser_fixture", "cleanup", "--root", fixture]);
}

export function assertCurrentImport(root: string, fixture: string, versionId: string) {
  return command(root, [join(root, "frontend/scripts/current-import-check.py"), join(root, "data/pmda/originals/イグザレルト錠２．５ｍｇ/630004_3339003F5020_1_08.xml"), fixture, versionId]);
}
