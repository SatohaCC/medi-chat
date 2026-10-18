#!/usr/bin/env node

import { spawn } from "node:child_process";
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
  initialDelayMs = 1000,
  maxDelayMs = 5000,
  onRestart = (delay) => {
    console.error(
      `\n[Backend Monitor] バックエンドプロセスが異常終了しました。${Math.round(delay / 1000)}秒後に自動再起動します...\n`,
    );
  },
} = {}) {
  let shouldRestart = true;
  let activeChild = null;
  let currentDelay = initialDelayMs;

  function stop() {
    shouldRestart = false;
    if (activeChild) {
      try {
        activeChild.kill("SIGTERM");
      } catch {
        // プロセスが既に終了している場合は無視
      }
    }
  }

  async function start() {
    while (shouldRestart) {
      const startTime = Date.now();
      const exitResult = await new Promise((resolvePromise) => {
        try {
          activeChild = spawn(command, args, {
            cwd,
            stdio: "inherit",
            shell: false,
          });
        } catch (err) {
          activeChild = null;
          resolvePromise({ code: 1, signal: null, error: err });
          return;
        }

        activeChild.on("error", (err) => {
          console.error(`[Backend Monitor] 起動エラー: ${err.message}`);
        });

        activeChild.on("exit", (code, signal) => {
          activeChild = null;
          resolvePromise({ code, signal });
        });
      });

      if (
        !shouldRestart ||
        exitResult.signal === "SIGINT" ||
        exitResult.signal === "SIGTERM"
      ) {
        break;
      }

      // 正常終了（code === 0 かつシグナルなし）の場合は再起動しない
      if (exitResult.code === 0 && !exitResult.signal) {
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
