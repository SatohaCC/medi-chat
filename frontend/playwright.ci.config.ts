import { defineConfig } from "@playwright/test";
import base from "./playwright.config";

// CIではOS固有の視覚基準（win32）とHMRのソース書き換えを扱えないため、
// モックAPIで動く機能E2Eだけを実行する。
export default defineConfig({
  ...base,
  testIgnore: [
    "**/visual-regression.spec.ts",
    "**/stylex-hmr.spec.ts",
    "**/spacing-theme.spec.ts",
  ],
});
