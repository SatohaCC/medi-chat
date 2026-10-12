import { spawn } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");

function execute(command, args, cwd) {
  return new Promise((resolveExit, reject) => {
    const child = spawn(command, args, { cwd, stdio: "inherit" });
    child.once("error", reject);
    child.once("exit", (code) => resolveExit(code ?? 1));
  });
}

async function runLayer(layer) {
  if (layer === "configured") {
    return execute(
      "uv",
      [
        "run",
        "--project",
        resolve(root, "backend"),
        "--locked",
        "python",
        "-m",
        "backend.infrastructure.cli.configured_e2e_gate",
      ],
      root,
    );
  }
  const args = [resolve(root, "frontend/node_modules/@playwright/test/cli.js"), "test"];
  if (layer === "real") args.push("--config=playwright.import-integration.config.ts");
  return execute(process.execPath, args, resolve(root, "frontend"));
}

export async function runE2e({ run = runLayer } = {}) {
  for (const layer of ["configured", "mock", "real"]) {
    const code = await run(layer);
    if (code !== 0) return code;
  }
  return 0;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    process.exitCode = await runE2e();
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
