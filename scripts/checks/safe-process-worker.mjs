import { workerData } from "node:worker_threads";

const { command, args, options, state, port } = workerData;
let result;
try {
  const { safeExecuteAsync } = await import("./safe-process.mjs");
  result = await safeExecuteAsync(command, args, options);
} catch (error) {
  result = { status: null, error, stdout: "", stderr: "" };
}
if (result.error) {
  result.error = { message: result.error.message, code: result.error.code };
}
port.postMessage(result);
port.close();
Atomics.store(state, 0, 1);
Atomics.notify(state, 0);
