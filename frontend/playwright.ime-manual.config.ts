import { defineConfig, devices } from "@playwright/test";

const currentURL = "http://127.0.0.1:3132",
  baselineURL = "http://127.0.0.1:3133";
const environment = (baseURL: string, dist: string) => ({
  MEDI_CHAT_NEXT_DIST_DIR: dist,
  MEDI_CHAT_TEST_UI: "1",
  NEXT_TELEMETRY_DISABLED: "1",
  NEXT_PUBLIC_API_URL: baseURL,
  NEXT_PUBLIC_WS_URL: `${baseURL.replace("http:", "ws:")}/api/ws`,
});
export default defineConfig({
  testDir: "./manual-e2e",
  workers: 1,
  retries: 0,
  timeout: 0,
  reporter: "list",
  outputDir: "../tmp/stylex-ime-artifacts",
  use: {
    ...devices["Desktop Chrome"],
    viewport: { width: 1280, height: 900 },
    locale: "ja-JP",
    deviceScaleFactor: 1,
    headless: process.env.MEDI_CHAT_IME_SMOKE === "1",
  },
  projects: [
    { name: "baseline", use: { baseURL: baselineURL } },
    { name: "current", use: { baseURL: currentURL } },
  ],
  webServer: [
    {
      command: "node scripts/serve-ime-baseline.mjs",
      url: baselineURL,
      reuseExistingServer: false,
      timeout: 120000,
      env: environment(baselineURL, ".next-ime-baseline"),
    },
    {
      command: "pnpm exec next dev --hostname 127.0.0.1 --port 3132",
      url: currentURL,
      reuseExistingServer: false,
      timeout: 120000,
      env: environment(currentURL, ".next-ime-manual"),
    },
  ],
});
