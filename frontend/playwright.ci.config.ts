import { defineConfig } from "@playwright/test";
import base from "./playwright.config";

const baseWebServer = Array.isArray(base.webServer)
  ? base.webServer[0]
  : base.webServer;

// CIではOS固有の視覚基準（win32）とHMRのソース書き換えを扱えないため、
// モックAPIで動く機能E2Eだけを実行する。
// registered-evidence は非公開のPMDA原本（data/pmda/originals）を必要とする
// source-data層のため、CIでは選択しない。ローカルでは通常どおり実行できる。
export default defineConfig({
  ...base,
  testIgnore: [
    "**/visual-regression.spec.ts",
    "**/stylex-hmr.spec.ts",
    "**/spacing-theme.spec.ts",
    "**/registered-evidence.spec.ts",
  ],
  // CIのワークフロー側でnext devを起動し、Playwrightはそのサーバーを再利用する。
  // Playwright自身に起動・停止させるとTurbopackの子プロセスが残り、ステップが終了しない。
  webServer: baseWebServer
    ? { ...baseWebServer, reuseExistingServer: true }
    : undefined,
});
