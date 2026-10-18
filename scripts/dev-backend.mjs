#!/usr/bin/env node

import { execFile, spawn } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
export const PROJECT_ROOT = resolve(__dirname, "..");
export const BACKEND_DIR = resolve(PROJECT_ROOT, "backend");

export function createSupervisor({
  command = "uv",
  args = [
    "run",
    "--locked",
    "uvicorn",
    "--app-dir",
    "..",
    "backend.main:app",
    "--port",
    "8000",
    "--reload",
  ],
  cwd = BACKEND_DIR,
  healthUrl = "http://127.0.0.1:8000/health",
  healthCheckIntervalMs = 1500,
  healthFailureThreshold = 3,
  startupTimeoutMs = 15000,
  initialDelayMs = 1000,
  maxDelayMs = 5000,
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
      try {
        execFile("taskkill", ["/pid", String(child.pid), "/t", "/f"], () => {});
      } catch {
        try {
          child.kill("SIGKILL");
        } catch {}
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
    while (shouldRestart) {
      const startTime = Date.now();
      let isReady = false;
      let consecutiveFailures = 0;
      let monitorTimer = null;

      const exitResult = await new Promise((resolvePromise) => {
        let completed = false;

        function finish(result) {
          if (!completed) {
            completed = true;
            if (monitorTimer) {
              clearInterval(monitorTimer);
              monitorTimer = null;
            }
            activeChild = null;
            resolvePromise(result);
          }
        }

        try {
          activeChild = spawn(command, args, {
            cwd,
            stdio: "inherit",
            shell: false,
          });
        } catch (err) {
          finish({ code: 1, signal: null, error: err });
          return;
        }

        activeChild.on("error", (err) => {
          console.error(`[Backend Monitor] 起動エラー: ${err.message}`);
          finish({ code: 1, signal: null, error: err });
        });

        activeChild.on("exit", (code, signal) => {
          finish({ code, signal });
        });

        // Uvicornの--reloadは子プロセスがクラッシュしても親が終了しないため、
        // healthUrlが指定されている場合は実サーバーの生存・応答状態を監視する
        if (healthUrl) {
          monitorTimer = setInterval(async () => {
            if (completed || !shouldRestart || !activeChild) return;

            let healthy = false;
            try {
              const controller = new AbortController();
              const timeoutId = setTimeout(() => controller.abort(), 1000);
              const res = await fetch(healthUrl, { signal: controller.signal });
              clearTimeout(timeoutId);
              if (res.ok) {
                healthy = true;
              }
            } catch {
              healthy = false;
            }

            if (completed || !shouldRestart || !activeChild) return;

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
                killProcess(childToKill);
              }
            }
          }, healthCheckIntervalMs);
        }
      });

      if (
        !shouldRestart ||
        exitResult.signal === "SIGINT" ||
        exitResult.signal === "SIGTERM"
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
  }

  return { start, stop };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const supervisor = createSupervisor();
  process.on("SIGINT", () => supervisor.stop());
  process.on("SIGTERM", () => supervisor.stop());
  supervisor.start();
}
