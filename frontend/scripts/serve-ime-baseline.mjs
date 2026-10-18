import { execFileSync, spawn } from "node:child_process";
import { createHash } from "node:crypto";
import {
  existsSync,
  mkdirSync,
  readFileSync,
  realpathSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { createRequire } from "node:module";
import { dirname, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { ensurePortAvailable } from "./owned-server.mjs";

const baselineHead = "7b46073b2fc07b9cad43072bf97ae86cbe13b916";
const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = resolve(frontendRoot, "..");
const fixtureRoot = resolve(repositoryRoot, "tmp/stylex-ime-baseline");
if (!fixtureRoot.startsWith(resolve(repositoryRoot, "tmp") + sep))
  throw new Error("Invalid baseline fixture root");
await ensurePortAvailable(3133);
mkdirSync(fixtureRoot, { recursive: true });
const files = execFileSync(
  "git",
  ["ls-tree", "-r", "--name-only", baselineHead, "frontend/app"],
  { cwd: repositoryRoot, encoding: "utf8" },
)
  .trim()
  .split(/\r?\n/)
  .filter((name) => /\.(ts|tsx|css)$/.test(name));
files.push("frontend/package.json", "frontend/tsconfig.json", "frontend/next.config.ts");
const manifest = {
  baselineHead,
  originalFiles: {},
  testEnvironmentOverrides: {
    postcss: "empty plugins: original source uses no Tailwind utilities",
    devIndicators: false,
    tsconfig: "original compiler options with test dist type includes",
  },
  compiler: true,
};
for (const name of files) {
  const original = execFileSync("git", ["show", `${baselineHead}:${name}`], {
    cwd: repositoryRoot,
  });
  const destination = resolve(fixtureRoot, relative("frontend", name));
  if (!destination.startsWith(fixtureRoot + sep))
    throw new Error("Invalid historical source path");
  let content = original;
  if (name.endsWith("tsconfig.json")) {
    const config = JSON.parse(original.toString("utf8"));
    config.include.push(
      ".next-ime-baseline/types/**/*.ts",
      ".next-ime-baseline/dev/types/**/*.ts",
    );
    content = Buffer.from(`${JSON.stringify(config, null, 2)}\n`);
  }
  if (name.endsWith("next.config.ts"))
    content = Buffer.from(
      original
        .toString("utf8")
        .replace(
          "  reactCompiler: true,",
          "  reactCompiler: true,\n  devIndicators: false,",
        ),
    );
  if (existsSync(destination) && !readFileSync(destination).equals(content))
    throw new Error(`Historical fixture was edited: ${name}`);
  mkdirSync(dirname(destination), { recursive: true });
  writeFileSync(destination, content);
  manifest.originalFiles[name] = createHash("sha256").update(original).digest("hex");
}
writeFileSync(
  join(fixtureRoot, "postcss.config.mjs"),
  "export default { plugins: {} };\n",
);
const modules = join(fixtureRoot, "node_modules"),
  expected = join(frontendRoot, "node_modules");
if (!existsSync(modules)) symlinkSync(expected, modules, "junction");
if (realpathSync(modules) !== realpathSync(expected))
  throw new Error("Unexpected baseline dependency junction");
writeFileSync(
  join(fixtureRoot, "baseline-provenance.json"),
  JSON.stringify(manifest, null, 2),
);
const require = createRequire(join(frontendRoot, "package.json"));
const child = spawn(
  process.execPath,
  [
    require.resolve("next/dist/bin/next"),
    "dev",
    "--hostname",
    "127.0.0.1",
    "--port",
    "3133",
  ],
  { cwd: fixtureRoot, stdio: "inherit", windowsHide: true, env: process.env },
);
process.on("SIGINT", () => child.kill("SIGINT"));
process.on("SIGTERM", () => child.kill("SIGTERM"));
child.on("error", (error) => {
  console.error(error);
  process.exitCode = 1;
});
child.on("exit", (code) => {
  process.exitCode = code ?? 1;
});
