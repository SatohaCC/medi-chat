import { defineConfig, devices } from "@playwright/test";

const baseURL = "http://127.0.0.1:3130";

export default defineConfig({
  testDir: "./e2e",
  testMatch: "stylex-build.spec.ts",
  workers: 1,
  retries: 0,
  reporter: "list",
  outputDir: "../tmp/stylex-production-results",
  use: { baseURL, trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command:
      "node node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3130",
    url: baseURL,
    reuseExistingServer: false,
    env: { MEDI_CHAT_NEXT_DIST_DIR: ".next-e2e-build" },
  },
});
