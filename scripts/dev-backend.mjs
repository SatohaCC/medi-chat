#!/usr/bin/env node

import { spawn } from "node:child_process";
import { randomUUID } from "node:crypto";
import { mkdirSync, createWriteStream } from "node:fs";
import { dirname, relative, resolve } from "node:path";
import { StringDecoder } from "node:string_decoder";
import { finished } from "node:stream/promises";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
export const PROJECT_ROOT = resolve(__dirname, "..");
export const BACKEND_DIR = resolve(PROJECT_ROOT, "backend");

// uvicornの--reloadはcwd配下の*.pyを監視する。backend/.venvを監視対象に含めると、
// 依存の同期や型検査でsite-packagesが書き換わるたびに再起動するため除外する。
// uvicornは--reload-excludeをディレクトリとして解決するため絶対パスで渡す。
export const RELOAD_EXCLUDED_DIRS = [resolve(BACKEND_DIR, ".venv")];

export const DEFAULT_UVICORN_ARGS = [
  "run",
  "--locked",
  "uvicorn",
  "--no-proxy-headers",
  "--app-dir",
  "..",
  "backend.main:app",
  "--port",
  "8000",
  "--reload",
  ...RELOAD_EXCLUDED_DIRS.flatMap((directory) => ["--reload-exclude", directory]),
  "--log-config",
  "../scripts/uvicorn-dev-logging.json",
];

function redactRuntimeLogLine(line) {
  return line
    .replace(/(["']?\b(?:proxy-)?authorization\b["']?\s*[:=]\s*)[^\r\n]*/gi, "$1[REDACTED]")
    .replace(/\bBearer\s+\S+/gi, "Bearer [REDACTED]")
    .replace(
      /(["']?\b(?:search[_-]?query|query|question)\b["']?\s*[=:]\s*)(?:"[^"]*"|'[^']*'|[^\r\n]*)/gi,
      "$1[REDACTED]",
    )
    .replace(
      /(["']?\b[A-Za-z0-9_-]*[_-]?(?:access[_-]?token|refresh[_-]?token|api[_-]?key|client[_-]?secret|private[_-]?key|secret[_-]?key|password|secret|token)\b["']?\s*[=:]\s*)(?:"[^"]*"|'[^']*'|[^&\s,;]+)/gi,
      "$1[REDACTED]",
    )
    .replace(/((?:https?:\/\/|\/)[^\s"'<>?]+)\?[^\s"'<>]*/g, "$1?[REDACTED]");
}

function createSessionLog({ logDirectory, stdout, stderr }) {
  mkdirSync(logDirectory, { recursive: true });
  const timestamp = new Date().toISOString().replaceAll(/[:.]/g, "-");
  const filePath = resolve(logDirectory, `dev-backend-${timestamp}-${process.pid}-${randomUUID()}.log`);
  const logStream = createWriteStream(filePath, { flags: "wx", encoding: "utf8" });
  const ready = new Promise((resolvePromise, rejectPromise) => {
    logStream.once("open", resolvePromise);
    logStream.once("error", rejectPromise);
  });
  const outputStreams = { stdout, stderr };

  function writeLine(streamName, line, terminalEnding) {
    const safeLine = redactRuntimeLogLine(line);
    outputStreams[streamName].write(`${safeLine}${terminalEnding}`);
    logStream.write(`${new Date().toISOString()} [${streamName}] ${safeLine}\n`);
  }

  function attach(child) {
    for (const streamName of ["stdout", "stderr"]) {
      const childStream = child[streamName];
      if (!childStream) continue;
      const decoder = new StringDecoder("utf8");
      let pending = "";
      childStream.on("data", (chunk) => {
        pending += decoder.write(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
        const lines = pending.split("\n");
        pending = lines.pop();
        for (const line of lines) writeLine(streamName, line, "\n");
      });
      childStream.on("end", () => {
        pending += decoder.end();
        if (pending) writeLine(streamName, pending, "");
      });
    }
  }

  return {
    filePath,
    ready,
    attach,
    async close() {
      logStream.end();
      await finished(logStream);
    },
  };
}

function waitForOutputClose(stream) {
  if (!stream || stream.readableEnded || stream.destroyed) return Promise.resolve();
  return new Promise((resolvePromise) => {
    const done = () => {
      stream.off("end", done);
      stream.off("close", done);
      stream.off("error", done);
      resolvePromise();
    };
    stream.once("end", done);
    stream.once("close", done);
    stream.once("error", done);
  });
}

export function createSupervisor({
  command = "uv",
  args = DEFAULT_UVICORN_ARGS,
  cwd = BACKEND_DIR,
  healthUrl = "http://127.0.0.1:8000/api?__medi_chat_dev_monitor=1",
  healthCheckIntervalMs = 1500,
  healthFailureThreshold = 3,
  startupTimeoutMs = 15000,
  initialDelayMs = 1000,
  maxDelayMs = 5000,
  logDirectory = resolve(PROJECT_ROOT, "tmp", "logs"),
  stdout = process.stdout,
  stderr = process.stderr,
  spawnProcess = spawn,
  onSessionLog = (filePath) => {
    console.error(`[Backend Monitor] セッションログ: ${relative(PROJECT_ROOT, filePath).replaceAll("\\", "/")}`);
  },
  onRestart = (delay) => {
    console.error(
      `\n[Backend Monitor] バックエンドプロセスが異常終了または応答不能になりました。${Math.round(delay / 1000)}秒後に自動再起動します...\n`,
    );
  },
} = {}) {
  let shouldRestart = true;
  let activeChild = null;
  let currentDelay = initialDelayMs;

  function killProcess(child) {
    if (!child || !child.pid) return;
    if (process.platform === "win32") {
      const forceStop = () => {
        try {
          child.kill("SIGKILL");
        } catch {}
      };
      let fallbackTimer = null;
      const clearFallback = () => {
        if (fallbackTimer) {
          clearTimeout(fallbackTimer);
          fallbackTimer = null;
        }
      };
      child.once("exit", clearFallback);
      try {
        const treeKiller = spawn("taskkill", ["/pid", String(child.pid), "/t", "/f"], {
          shell: false,
          stdio: "ignore",
          windowsHide: true,
        });
        treeKiller.once("error", forceStop);
        treeKiller.once("close", (code) => {
          if (code !== 0) forceStop();
        });
        treeKiller.unref();
        fallbackTimer = setTimeout(forceStop, 1000);
        fallbackTimer.unref();
      } catch {
        forceStop();
      }
    } else {
      try {
        child.kill("SIGTERM");
      } catch {}
    }
  }

  function stop() {
    shouldRestart = false;
    if (activeChild) {
      killProcess(activeChild);
      activeChild = null;
    }
  }

  async function start() {
    const sessionLog = createSessionLog({ logDirectory, stdout, stderr });
    await sessionLog.ready;
    try {
      onSessionLog(sessionLog.filePath);
      while (shouldRestart) {
        const startTime = Date.now();
        let isReady = false;
        let consecutiveFailures = 0;
        let monitorTimer = null;
        let outputDrainTimer = null;
        let healthRestartRequested = false;
        let exitSeen = false;

        const exitResult = await new Promise((resolvePromise) => {
          let completed = false;

          function finish(result) {
            if (!completed) {
              completed = true;
              if (monitorTimer) {
                clearInterval(monitorTimer);
                monitorTimer = null;
              }
              if (outputDrainTimer) {
                clearTimeout(outputDrainTimer);
                outputDrainTimer = null;
              }
              activeChild = null;
              resolvePromise(result);
            }
          }

          try {
            activeChild = spawnProcess(command, args, {
              cwd,
              stdio: ["inherit", "pipe", "pipe"],
              shell: false,
              detached: process.platform === "win32",
            });
          } catch (err) {
            finish({ code: 1, signal: null, error: err });
            return;
          }

          const child = activeChild;
          sessionLog.attach(child);

          child.on("error", (err) => {
            console.error(`[Backend Monitor] 起動エラー: ${err.message}`);
            finish({ code: 1, signal: null, error: err });
          });

          child.on("exit", (code, signal) => {
            exitSeen = true;
            outputDrainTimer = setTimeout(() => finish({ code, signal }), 1000);
            Promise.all([waitForOutputClose(child.stdout), waitForOutputClose(child.stderr)])
              .then(() => finish({ code, signal }));
          });

          child.on("close", (code, signal) => {
            exitSeen = true;
            finish({ code, signal });
          });

          // Uvicornの--reloadは子プロセスがクラッシュしても親が終了しないため、
          // healthUrlが指定されている場合は実サーバーの生存・応答状態を監視する
          if (healthUrl) {
            monitorTimer = setInterval(async () => {
              if (completed || exitSeen || !shouldRestart || !activeChild) return;

              let healthy = false;
              try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 1000);
                const res = await fetch(healthUrl, { signal: controller.signal });
                clearTimeout(timeoutId);
                if (res.ok) {
                  healthy = true;
                } else if (res.status === 401) {
                  // A protected, running server rejects this unauthenticated probe.
                  const body = await res.json().catch(() => null);
                  healthy = body?.detail?.code === "authentication_required";
                }
              } catch {
                healthy = false;
              }

              if (completed || exitSeen || !shouldRestart || !activeChild) return;

              if (healthy) {
                isReady = true;
                consecutiveFailures = 0;
                return;
              }

              if (!isReady) {
                if (Date.now() - startTime > startupTimeoutMs) {
                  if (monitorTimer) {
                    clearInterval(monitorTimer);
                    monitorTimer = null;
                  }
                  console.error(
                    `[Backend Monitor] 起動タイムアウト: サーバーが${Math.round(startupTimeoutMs / 1000)}秒以内に応答可能になりませんでした。再起動します...`,
                  );
                  const childToKill = activeChild;
                  healthRestartRequested = true;
                  killProcess(childToKill);
                }
              } else {
                consecutiveFailures++;
                if (consecutiveFailures >= healthFailureThreshold) {
                  if (monitorTimer) {
                    clearInterval(monitorTimer);
                    monitorTimer = null;
                  }
                  console.error(
                    `[Backend Monitor] サーバー応答途絶: ヘルスチェックが${healthFailureThreshold}回連続で失敗しました。再起動します...`,
                  );
                  const childToKill = activeChild;
                  healthRestartRequested = true;
                  killProcess(childToKill);
                }
              }
            }, healthCheckIntervalMs);
          }
        });

        if (
          !shouldRestart ||
          // On POSIX, our health-check restart also terminates the child with SIGTERM.
          (!healthRestartRequested &&
            (exitResult.signal === "SIGINT" || exitResult.signal === "SIGTERM"))
        ) {
          break;
        }

        // 正常終了（code === 0 かつシグナルなし、かつエラーなし）の場合は再起動しない
        if (exitResult.code === 0 && !exitResult.signal && !exitResult.error) {
          break;
        }

        const elapsed = Date.now() - startTime;
        if (elapsed < 3000) {
          currentDelay = Math.min(currentDelay * 1.5, maxDelayMs);
        } else {
          currentDelay = initialDelayMs;
        }

        onRestart(currentDelay);
        await new Promise((resolveDelay) => setTimeout(resolveDelay, currentDelay));
      }
    } finally {
      await sessionLog.close();
    }
  }

  return { start, stop };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const supervisor = createSupervisor();
  process.on("SIGINT", () => supervisor.stop());
  process.on("SIGTERM", () => supervisor.stop());
  supervisor.start();
}
