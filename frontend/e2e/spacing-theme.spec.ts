import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test } from "./helpers/test";

for (const width of [390, 1280]) {
  test(`実配信CSSで検索画面の余白とテーマを維持する (${width})`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.route("**/api/medicines", (route) =>
      route.fulfill({ json: { generation_id: "test-spacing", items: [] } }),
    );
    await page.goto("/search");
    await expect(page.getByRole("searchbox", { name: "検索キーワード" })).toBeVisible();
    await expect(page.getByRole("main")).toHaveCSS(
      "padding-left",
      width <= 600 ? "16px" : "24px",
    );
    await expect(page.getByRole("main")).toHaveCSS("row-gap", "16px");
    const form = page
      .locator("form")
      .filter({ has: page.getByRole("searchbox", { name: "検索キーワード" }) });
    await expect(form).toHaveCSS("padding-left", "12px");
    await expect(form).toHaveCSS("column-gap", "8px");
    await page.screenshot({ path: `../tmp/search-real-${width}.png` });
    await page.reload();
    await expect(page.getByRole("main")).toHaveCSS(
      "padding-left",
      width <= 600 ? "16px" : "24px",
    );
  });
}

test("余白トークンへの変更と復元を実CSSへHMRし、入力を保持する", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.route("**/api/medicines", (route) =>
    route.fulfill({ json: { generation_id: "test-spacing", items: [] } }),
  );
  await page.goto("/search");
  const input = page.getByRole("searchbox", { name: "検索キーワード" });
  await input.fill("テスト入力を保持");
  const main = page.getByRole("main");
  await expect(main).toHaveCSS("padding-left", "24px");
  const documentTime = await page.evaluate(() => performance.timeOrigin);
  const source = resolve(
    "features/keyword-search/components/KeywordSearchScreen.styles.ts",
  );
  const original = readFileSync(source, "utf8");
  const changed = original.replace(
    'padding: "var(--space-page)"',
    'padding: "var(--space-8)"',
  );
  expect(changed).not.toBe(original);
  try {
    writeFileSync(source, changed);
    await expect(main).toHaveCSS("padding-left", "32px", { timeout: 30000 });
    await expect(input).toHaveValue("テスト入力を保持");
    expect(await page.evaluate(() => performance.timeOrigin)).toBe(documentTime);
  } finally {
    writeFileSync(source, original);
  }
  await expect(main).toHaveCSS("padding-left", "24px", { timeout: 30000 });
  await expect(input).toHaveValue("テスト入力を保持");
});

test("新しい余白トークンの定義と参照を同時更新しても余白を維持する", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.route("**/api/medicines", (route) =>
    route.fulfill({ json: { generation_id: "test-spacing", items: [] } }),
  );
  await page.goto("/search");
  const main = page.getByRole("main");
  await expect(main).toHaveCSS("padding-left", "24px");
  const source = resolve(
    "features/keyword-search/components/KeywordSearchScreen.styles.ts",
  );
  const tokens = resolve("styles/tokens.css");
  const original = readFileSync(source, "utf8"),
    originalTokens = readFileSync(tokens, "utf8");
  try {
    writeFileSync(
      tokens,
      originalTokens.replace(":root {", ":root { --test-spacing-regression: 28px;"),
    );
    writeFileSync(
      source,
      original.replace(
        'padding: "var(--space-page)"',
        'padding: "var(--test-spacing-regression)"',
      ),
    );
    await expect(main).toHaveCSS("padding-left", "28px", { timeout: 30000 });
  } finally {
    writeFileSync(source, original);
    writeFileSync(tokens, originalTokens);
  }
  await expect(main).toHaveCSS("padding-left", "24px", { timeout: 30000 });
});
