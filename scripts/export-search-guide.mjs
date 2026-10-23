// Generate committed frontend display data from the typed Python definitions.
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

execFileSync("uv", ["run", "--project", "backend", "--locked", "python", "-m", "backend.infrastructure.cli.export_search_guide", ...process.argv.slice(2)], {
  cwd: fileURLToPath(new URL("..", import.meta.url)),
  stdio: "inherit",
});
