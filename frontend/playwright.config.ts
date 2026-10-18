import { defineConfig, devices } from "@playwright/test";

const baseURL = "http://127.0.0.1:3100";

export default defineConfig({
  testDir: "./e2e",
  outputDir: "./test-results/mock",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  workers: 1,
  reporter: "list",
  use: {
    baseURL,
    locale: "ja-JP",
    deviceScaleFactor: 1,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "pnpm exec next dev --hostname 127.0.0.1 --port 3100",
    url: baseURL,
    reuseExistingServer: false,
    timeout: 120_000,
    env: {
      MEDI_CHAT_NEXT_DIST_DIR: ".next-e2e-mock",
      NEXT_PUBLIC_API_URL: baseURL,
      NEXT_PUBLIC_WS_URL: "ws://127.0.0.1:3100/api/ws",
      NEXT_TELEMETRY_DISABLED: "1",
      MEDI_CHAT_TEST_UI: "1",
    },
  },
});
