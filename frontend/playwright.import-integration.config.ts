import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e-real",
  fullyParallel: false,
  workers: 1,
  timeout: 120_000,
  retries: 0,
  reporter: "list",
  use: { baseURL: "http://127.0.0.1:3110", trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "pnpm exec next dev --hostname 127.0.0.1 --port 3110",
    url: "http://127.0.0.1:3110",
    reuseExistingServer: false,
    timeout: 120_000,
    env: {
      MEDI_CHAT_NEXT_DIST_DIR: ".next-e2e-real",
      NEXT_PUBLIC_API_URL: "http://127.0.0.1:3211",
      NEXT_PUBLIC_WS_URL: "ws://127.0.0.1:3211/api/ws",
      NEXT_TELEMETRY_DISABLED: "1",
    },
  },
});
