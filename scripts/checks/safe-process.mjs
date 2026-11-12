import { spawn, spawnSync } from "node:child_process";
import { closeSync, existsSync, mkdirSync, openSync, readFileSync, readSync, statSync, unlinkSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { MessageChannel, receiveMessageOnPort, Worker } from "node:worker_threads";
import { StringDecoder } from "node:string_decoder";

const ROOT = fileURLToPath(new URL("../../", import.meta.url));
const TMP_DIR = resolve(ROOT, "tmp/quality/safe-process");

function ensureTmpDir() {
  if (!existsSync(TMP_DIR)) {
    mkdirSync(TMP_DIR, { recursive: true });
  }
}

function createTempFileDescriptors() {
  ensureTmpDir();
  const id = `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  const outPath = resolve(TMP_DIR, `${id}.out.tmp`);
  const errPath = resolve(TMP_DIR, `${id}.err.tmp`);
  const outFd = openSync(outPath, "w+");
  const errFd = openSync(errPath, "w+");
  let closed = false;
  const close = () => {
    if (closed) return;
    closed = true;
    try { closeSync(outFd); } catch {}
    try { closeSync(errFd); } catch {}
  };
  return {
    outPath,
    errPath,
    outFd,
    errFd,
    close,
    cleanup: () => {
      close();
      try { if (existsSync(outPath)) unlinkSync(outPath); } catch {}
      try { if (existsSync(errPath)) unlinkSync(errPath); } catch {}
    },
  };
}

export function readTail(path, maxChars = 4000) {
  try {
    if (!existsSync(path)) return "";
    const stats = statSync(path);
    if (stats.size === 0) return "";
    const bytesToRead = Math.min(stats.size, maxChars * 4);
    const buffer = Buffer.alloc(bytesToRead);
    const fd = openSync(path, "r");
    readSync(fd, buffer, 0, bytesToRead, stats.size - bytesToRead);
    closeSync(fd);
    const text = buffer.toString("utf8");
    return text.length > maxChars ? text.slice(-maxChars) : text;
  } catch {
    return "";
  }
}

export function safeSpawnSync(command, args = [], options = {}) {
  // If stdio is already customized and not containing 'pipe', try direct spawnSync
  const stdio = options.stdio;
  const isPiped = !stdio || stdio === "pipe" || (Array.isArray(stdio) && stdio.some((s) => s === "pipe"));

  if (!isPiped) {
    return spawnSync(command, args, options);
  }

  // A worker can monitor file sizes while the calling thread waits synchronously.
  // Worker messages use shared memory, without child-process named-pipe stdio.
  const state = new Int32Array(new SharedArrayBuffer(4));
  const { port1, port2 } = new MessageChannel();
  const worker = new Worker(new URL("./safe-process-worker.mjs", import.meta.url), {
    workerData: { command, args, options, state, port: port2 },
    transferList: [port2],
    execArgv: [],
  });
  try {
    Atomics.wait(state, 0, 0);
    const { message: result } = receiveMessageOnPort(port1);
    if (result.error) result.error = Object.assign(new Error(result.error.message), result.error);
    if (result.stdout instanceof Uint8Array) result.stdout = Buffer.from(result.stdout);
    if (result.stderr instanceof Uint8Array) result.stderr = Buffer.from(result.stderr);
    result.output = [null, result.stdout, result.stderr];
    return result;
  } finally {
    port1.close();
    worker.unref();
  }
}

function readBounded(path, budget, encoding = "utf8") {
  const bytes = Math.min(statSync(path).size, budget);
  const buffer = Buffer.alloc(bytes);
  const fd = openSync(path, "r");
  let count;
  try {
    count = readSync(fd, buffer, 0, bytes, 0);
  } finally {
    closeSync(fd);
  }
  const output = buffer.subarray(0, count);
  return encoding === "buffer" ? output : new StringDecoder(encoding).write(output);
}

export function safeExecFileSync(file, args = [], options = {}) {
  const result = safeSpawnSync(file, args, options);
  if (result.error) throw result.error;
  if (result.status !== 0) {
    const error = new Error(`Command failed: ${file} ${args.join(" ")}\n${result.stderr || result.stdout}`);
    error.status = result.status;
    error.stdout = result.stdout;
    error.stderr = result.stderr;
    throw error;
  }
  return result.stdout;
}

function terminateProcessTree(child) {
  if (!child?.pid) return;
  if (process.platform === "win32") {
    const res = spawnSync("taskkill", ["/PID", String(child.pid), "/T", "/F"], {
      stdio: "ignore",
      windowsHide: true,
      timeout: 2000,
    });
    if (res.error || res.status !== 0) {
      try {
        child.kill();
      } catch {
        // Ignore already exited process
      }
    }
    return;
  }
  try {
    process.kill(-child.pid, "SIGTERM");
  } catch {
    try {
      child.kill("SIGTERM");
    } catch {
      // Ignore already exited process
    }
  }
  const killTimer = setTimeout(() => {
    try {
      process.kill(-child.pid, "SIGKILL");
    } catch {
      try {
        child.kill("SIGKILL");
      } catch {
        // Ignore already exited process
      }
    }
  }, 150);
  killTimer.unref?.();
}

export function safeExecuteAsync(command, argsOrOptions = [], maybeOptions = {}) {
  const args = Array.isArray(argsOrOptions) ? argsOrOptions : [];
  const options = Array.isArray(argsOrOptions) ? maybeOptions : argsOrOptions;

  return new Promise((resolvePromise) => {
    const temp = createTempFileDescriptors();
    let child;
    let timer;
    let forceFinishTimer;
    let timedOut = false;
    let limitTimer;
    let limitError = null;
    const maxBuffer = options.maxBuffer ?? 16 * 1024 * 1024;
    const outputSize = () => statSync(temp.outPath).size + statSync(temp.errPath).size;
    const bufferError = () => Object.assign(new Error("maxBuffer exceeded"), { code: "ENOBUFS" });

    try {
      const spawnArgs = Array.isArray(argsOrOptions) ? [command, args, { ...options }] : [command, { ...options }];
      const spawnOpts = Array.isArray(argsOrOptions) ? spawnArgs[2] : spawnArgs[1];
      delete spawnOpts.timeout;
      delete spawnOpts.tailMaxChars;
      spawnOpts.stdio = ["ignore", temp.outFd, temp.errFd];
      if (spawnOpts.detached === undefined && spawnOpts.shell && process.platform !== "win32") {
        spawnOpts.detached = true;
      }

      child = Array.isArray(argsOrOptions)
        ? spawn(command, args, spawnOpts)
        : spawn(command, spawnOpts);
    } catch (error) {
      temp.cleanup();
      resolvePromise({ status: null, error, stdout: "", stderr: "" });
      return;
    }

    const timeoutErrorFor = () => {
      const timeoutError = new Error("ETIMEDOUT");
      timeoutError.code = "ETIMEDOUT";
      return timeoutError;
    };

    if (Number.isFinite(maxBuffer)) {
      limitTimer = setInterval(() => {
        if (!limitError && outputSize() > maxBuffer) {
          limitError = bufferError();
          terminateProcessTree(child);
          forceFinishTimer = setTimeout(() => finish(null, limitError), 50);
        }
      }, 10);
    }

    if (options.timeout) {
      timer = setTimeout(() => {
        timedOut = true;
        terminateProcessTree(child);
        forceFinishTimer = setTimeout(() => {
          finish(null, timeoutErrorFor());
        }, 50);
        forceFinishTimer.unref?.();
      }, options.timeout);
    }

    let settled = false;
    function finish(status, error) {
      if (settled) return;
      settled = true;
      if (timer) clearTimeout(timer);
      if (limitTimer) clearInterval(limitTimer);
      if (forceFinishTimer) clearTimeout(forceFinishTimer);

      temp.close();

      let stdout = "";
      let stderr = "";
      try {
        if (outputSize() > maxBuffer) limitError ??= bufferError();
        if (options.tailMaxChars) {
          stdout = readTail(temp.outPath, options.tailMaxChars);
          stderr = readTail(temp.errPath, options.tailMaxChars);
        } else {
          const outBytes = Math.min(statSync(temp.outPath).size, maxBuffer);
          stdout = readBounded(temp.outPath, outBytes, options.encoding);
          stderr = readBounded(temp.errPath, maxBuffer - outBytes, options.encoding);
        }
      } catch (readError) {
        error ??= readError;
      }
      temp.cleanup();

      resolvePromise({ status: limitError ? null : status, error: limitError ?? error ?? null, stdout, stderr, pid: child.pid });
    }

    child.on("error", (error) => finish(null, timedOut ? timeoutErrorFor() : error));
    child.on("close", (status) => finish(timedOut ? null : status, timedOut ? timeoutErrorFor() : null));
  });
}
