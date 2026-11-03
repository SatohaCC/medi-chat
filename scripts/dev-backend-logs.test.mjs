import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import os from "node:os";
import { join } from "node:path";
import { PassThrough } from "node:stream";
import test from "node:test";
import { createSupervisor } from "./dev-backend.mjs";

test("supervisor streams sanitized output into one session log across a restart", async (t) => {
  const logDirectory = await mkdtemp(join(os.tmpdir(), "medi-chat-runtime-logs-"));
  t.after(() => rm(logDirectory, { recursive: true, force: true }));

  const visibleStdout = new PassThrough();
  const visibleStderr = new PassThrough();
  let stdoutText = "";
  let stderrText = "";
  visibleStdout.on("data", (chunk) => { stdoutText += chunk.toString(); });
  visibleStderr.on("data", (chunk) => { stderrText += chunk.toString(); });

  const sessionLogs = [];
  let attempts = 0;
  let restarts = 0;
  const supervisor = createSupervisor({
    command: "synthetic-child",
    args: [],
    healthUrl: null,
    logDirectory,
    stdout: visibleStdout,
    stderr: visibleStderr,
    onSessionLog: (path) => { sessionLogs.push(path); },
    initialDelayMs: 1,
    maxDelayMs: 1,
    onRestart: () => { restarts++; },
    spawnProcess: () => {
      const attempt = attempts++;
      const child = new EventEmitter();
      child.stdout = new PassThrough();
      child.stderr = new PassThrough();
      queueMicrotask(() => {
        child.stdout.write(attempt === 0
          ? "GET /api/search?query=private-medical-term\nquery=private-medical-term\n"
          : "restarted backend output\n");
        child.stderr.write(attempt === 0
          ? "Authorization: Bearer private-token\nOPENAI_API_KEY=private-api-key\n"
          : "");
        child.stdout.end();
        child.stderr.end();
        child.emit("exit", attempt === 0 ? 1 : 0, null);
      });
      return child;
    },
  });

  await supervisor.start();

  assert.equal(restarts, 1);
  assert.equal(sessionLogs.length, 1);
  assert.match(stdoutText, /GET \/api\/search\?\[REDACTED\]/);
  assert.match(stdoutText, /query=\[REDACTED\]/);
  assert.match(stdoutText, /restarted backend output/);
  assert.match(stderrText, /Authorization: \[REDACTED\]/);
  assert.match(stderrText, /OPENAI_API_KEY=\[REDACTED\]/);
  assert.doesNotMatch(`${stdoutText}\n${stderrText}`, /private-medical-term|private-token|private-api-key/);

  const sessionLog = await readFile(sessionLogs[0], "utf8");
  assert.match(sessionLog, /\[stdout\] GET \/api\/search\?\[REDACTED\]/);
  assert.match(sessionLog, /\[stdout\] query=\[REDACTED\]/);
  assert.match(sessionLog, /\[stdout\] restarted backend output/);
  assert.match(sessionLog, /\[stderr\] Authorization: \[REDACTED\]/);
  assert.match(sessionLog, /\[stderr\] OPENAI_API_KEY=\[REDACTED\]/);
  assert.doesNotMatch(sessionLog, /private-medical-term|private-token|private-api-key/);
});
