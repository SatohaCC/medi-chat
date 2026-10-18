import assert from "node:assert/strict";
import test from "node:test";
import { createSupervisor } from "./dev-backend.mjs";

test("supervisor does not restart on clean exit (code 0)", async () => {
  let restarts = 0;
  const supervisor = createSupervisor({
    command: process.execPath,
    args: ["-e", "process.exit(0)"],
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
    initialDelayMs: 10,
    onRestart: () => {
      restarts++;
    },
  });

  supervisor.stop();
  await supervisor.start();
  assert.equal(restarts, 0);
});
