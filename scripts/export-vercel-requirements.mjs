import { spawnSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../", import.meta.url));
const exported = spawnSync("uv", [
  "export", "--project", "backend", "--locked", "--no-dev",
  "--no-emit-project", "--no-hashes", "--no-header", "--format", "requirements-txt",
], { cwd: root, encoding: "utf8", shell: false });
if (exported.status !== 0) {
  process.stderr.write(exported.stderr || "uv export failed\n");
  process.exit(exported.status || 1);
}
const generated = "# Generated from backend/uv.lock; update with pnpm vercel:requirements.\n"
  + exported.stdout.replace(/\r\n/g, "\n");
const target = new URL("../requirements.txt", import.meta.url);
if (process.argv.includes("--check")) {
  if (readFileSync(target, "utf8").replace(/\r\n/g, "\n") !== generated) {
    process.stderr.write("requirements.txt is stale; run pnpm vercel:requirements.\n");
    process.exit(1);
  }
  process.stdout.write("Vercel runtime requirements match backend/uv.lock.\n");
} else {
  writeFileSync(target, generated);
}
