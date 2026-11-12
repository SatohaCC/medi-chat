// In-process test runner for node:test files.
// Avoids child_process named-pipe IPC creation inside Node's native --test runner,
// ensuring compatibility with restricted Windows/DSH sandboxes.
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { run } from "node:test";
import { tap } from "node:test/reporters";

const ROOT = fileURLToPath(new URL("../../", import.meta.url));

async function main() {
  const rawArgs = process.argv.slice(2);
  const timeoutArg = rawArgs.find(arg => arg.startsWith("--test-timeout="));
  const timeout = timeoutArg ? Number(timeoutArg.split("=")[1]) : 60_000;
  const files = rawArgs.filter((arg) => !arg.startsWith("-") && arg.endsWith(".mjs"));
  if (!Number.isFinite(timeout) || timeout <= 0 || rawArgs.some(arg => arg !== timeoutArg && !files.includes(arg))) {
    throw new Error("Expected .mjs test paths and an optional positive --test-timeout=<ms>");
  }

  if (!files.length) {
    console.error("No test files specified");
    process.exitCode = 1;
    return;
  }

  const tests = run({ files: files.map(file => resolve(ROOT, file)), isolation: "none", timeout });
  tests.on("test:fail", () => { process.exitCode = 1; });
  tests.on("error", error => { console.error(error); process.exitCode = 1; });
  tests.compose(tap).pipe(process.stdout);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
