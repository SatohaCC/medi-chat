const { readFileSync } = require("node:fs");
const { createRequire } = require("node:module");
const { join } = require("node:path");

function loadRootEnvironment(root) {
  let contents;
  try {
    contents = readFileSync(join(root, ".env.local"), "utf8");
  } catch (error) {
    if (error.code === "ENOENT") return;
    throw error;
  }
  const frontendRequire = createRequire(join(__dirname, "../frontend/package.json"));
  const nextRequire = createRequire(frontendRequire.resolve("next/package.json"));
  // Use Next's parser/expansion, but provide exactly one file instead of scanning.
  nextRequire("@next/env").processEnv(
    [{ path: ".env.local", contents, env: {} }], root, console, true,
  );
}

module.exports = { loadRootEnvironment };
