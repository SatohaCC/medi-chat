import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./shared",
  testMatch: "**/*.browser.spec.ts",
  outputDir: "./test-results/shared",
  workers: 1,
  retries: 0,
  reporter: "list",
  use: { baseURL: "http://127.0.0.1:6007", trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "pnpm exec storybook dev --ci --host 127.0.0.1 --port 6007 --no-open",
    url: "http://127.0.0.1:6007",
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
