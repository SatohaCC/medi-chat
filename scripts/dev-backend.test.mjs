import assert from "node:assert/strict";
import test from "node:test";
import { createSupervisor } from "./dev-backend.mjs";

test("supervisor does not restart on clean exit (code 0)", async () => {
  let restarts = 0;
  const supervisor = createSupervisor({
    command: process.execPath,
    args: ["-e", "process.exit(0)"],
    healthUrl: null,
    initialDelayMs: 10,
    onRestart: () => {
      restarts++;
    },
  });

  await supervisor.start();
  assert.equal(restarts, 0);
});

test("supervisor restarts on crash exit (non-zero code)", async () => {
  let restarts = 0;
  const supervisor = createSupervisor({
    command: process.execPath,
    args: ["-e", "process.exit(1)"],
    healthUrl: null,
    initialDelayMs: 10,
    maxDelayMs: 20,
    onRestart: () => {
      restarts++;
      if (restarts >= 2) {
        supervisor.stop();
      }
    },
  });

  await supervisor.start();
  assert.equal(restarts, 2);
});

test("supervisor stops immediately when stop() is invoked", async () => {
  let restarts = 0;
  const supervisor = createSupervisor({
    command: process.execPath,
    args: ["-e", "process.exit(1)"],
    healthUrl: null,
    initialDelayMs: 10,
    onRestart: () => {
      restarts++;
    },
  });

  supervisor.stop();
  await supervisor.start();
  assert.equal(restarts, 0);
});

test("supervisor handles spawn error (ENOENT) without hanging", async () => {
  let restarts = 0;
  const supervisor = createSupervisor({
    command: "__non_existent_command_xyz_12345__",
    args: [],
    healthUrl: null,
    initialDelayMs: 10,
    onRestart: () => {
      restarts++;
      supervisor.stop();
    },
  });

  await supervisor.start();
  assert.equal(restarts, 1);
});

test("supervisor detects unresponsive server via healthUrl and restarts", async () => {
  let restarts = 0;
  // 一切ポートを開かないコマンドを実行し、ヘルスチェックのタイムアウトで再起動されることを確認
  const supervisor = createSupervisor({
    command: process.execPath,
    args: [
      "-e",
      "setInterval(() => {}, 1000);", // 終了せず待機するだけのプロセス
    ],
    healthUrl: "http://127.0.0.1:54321/health", // リスンしていないポート
    healthCheckIntervalMs: 20,
    startupTimeoutMs: 60,
    initialDelayMs: 10,
    onRestart: () => {
      restarts++;
      supervisor.stop();
    },
  });

  await supervisor.start();
  assert.equal(restarts, 1);
});
