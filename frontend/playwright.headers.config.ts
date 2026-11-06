import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e-headers",
  outputDir: "./test-results/headers",
  workers: 1,
  retries: 0,
  use: { baseURL: "http://127.0.0.1:3124" },
  webServer: {
    command:
      "pnpm exec next build && pnpm exec next start --hostname 127.0.0.1 --port 3124",
    url: "http://127.0.0.1:3124/favicon.ico",
    reuseExistingServer: false,
    timeout: 180_000,
    env: {
      MEDI_CHAT_NEXT_DIST_DIR: ".next-e2e-build",
      NEXT_TELEMETRY_DISABLED: "1",
      PYTHON_DOTENV_DISABLED: "1",
    },
  },
});
