import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { randomUUID } from "node:crypto";
import test from "node:test";
import {
  PROJECT_ROOT,
  LOG_DIRECTORY,
  resolveSessionLogPath,
  scanSessionLog,
} from "./check-logs.mjs";

const SCRIPT_PATH = fileURLToPath(new URL("./check-logs.mjs", import.meta.url));
const iso = (hour, minute = 0) => `2026-11-03T${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}:00.000Z`;
const logLine = (timestamp, stream, message) => `${timestamp} [${stream}] ${message}`;

test("scanner reports Uvicorn errors and access 5xx, excluding 4xx and generic exception text", () => {
  const content = [
    logLine(iso(10), "stdout", 'INFO: 127.0.0.1 - "GET /api HTTP/1.1" 404 Not Found'),
    logLine(iso(10), "stdout", 'INFO: 127.0.0.1 - "GET /api HTTP/1.1" 503 Service Unavailable'),
    logLine(iso(10), "stderr", "ERROR: request handling failed"),
    logLine(iso(10), "stderr", "INFO: recovered after Exception was reported"),
  ].join("\n");

  assert.deepEqual(scanSessionLog(content), [
    { line: 2, categories: ["HTTP 503"] },
    { line: 3, categories: ["ERROR"] },
  ]);
});

test("scanner applies an inclusive ISO since boundary", () => {
  const content = [
    logLine(iso(10), "stdout", 'INFO: app - "GET /before HTTP/1.1" 500 Internal Server Error'),
    logLine(iso(10, 1), "stdout", 'INFO: app - "GET /at HTTP/1.1" 500 Internal Server Error'),
  ].join("\n");

  assert.deepEqual(scanSessionLog(content, Date.parse(iso(10, 1))), [
    { line: 2, categories: ["HTTP 500"] },
  ]);
});

test("session log paths are restricted to generated files directly under tmp/logs", async (t) => {
  const outsideDirectory = await mkdtemp(join(tmpdir(), "medi-chat-log-path-"));
  t.after(() => rm(outsideDirectory, { recursive: true, force: true }));
  const outsidePath = join(outsideDirectory, `dev-backend-${randomUUID()}.log`);
  await writeFile(outsidePath, "");

  assert.throws(() => resolveSessionLogPath(outsidePath), /under tmp\/logs/);
  assert.throws(() => resolveSessionLogPath(resolve(LOG_DIRECTORY, "session.log")), /generated session log/);
});

test("CLI reports locations and categories without printing log lines", async (t) => {
  await mkdir(LOG_DIRECTORY, { recursive: true });
  const filename = `dev-backend-${new Date().toISOString().replaceAll(/[:.]/g, "-")}-${process.pid}-${randomUUID()}.log`;
  const sessionLog = resolve(LOG_DIRECTORY, filename);
  t.after(() => rm(sessionLog, { force: true }));
  await writeFile(sessionLog, [
    logLine(iso(0), "stdout", 'INFO: app - "GET /stale HTTP/1.1" 500 Internal Server Error'),
    logLine(iso(1), "stdout", 'INFO: app - "GET /api/search?private-medical-term HTTP/1.1" 503 Service Unavailable'),
    logLine(iso(1), "stderr", "ERROR: Authorization: Bearer private-token"),
  ].join("\n"), "utf8");

  const result = spawnSync(process.execPath, [
    SCRIPT_PATH,
    join("tmp", "logs", filename),
    "--since",
    iso(1),
  ], { cwd: PROJECT_ROOT, encoding: "utf8" });

  assert.equal(result.status, 1, result.stderr);
  assert.match(result.stdout, /:2 HTTP 503/);
  assert.match(result.stdout, /:3 ERROR/);
  assert.doesNotMatch(`${result.stdout}\n${result.stderr}`, /private-medical-term|private-token|\/stale/);
  assert.doesNotMatch(`${result.stdout}\n${result.stderr}`, /Service Unavailable|Authorization:/);
});

test("CLI rejects a log outside tmp/logs without echoing its path", async (t) => {
  const outsideDirectory = await mkdtemp(join(tmpdir(), "medi-chat-log-outside-"));
  t.after(() => rm(outsideDirectory, { recursive: true, force: true }));
  const outsidePath = join(outsideDirectory, `dev-backend-${randomUUID()}.log`);
  await writeFile(outsidePath, logLine(iso(1), "stderr", "ERROR: private data"));

  const result = spawnSync(process.execPath, [SCRIPT_PATH, outsidePath], {
    cwd: dirname(PROJECT_ROOT),
    encoding: "utf8",
  });

  assert.equal(result.status, 2);
  assert.match(result.stderr, /under tmp\/logs/);
  assert.doesNotMatch(`${result.stdout}\n${result.stderr}`, /private data|medi-chat-log-outside/);
});
