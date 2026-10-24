import { type BrowserContext, expect, test } from "@playwright/test";

const principal = () => ({ user_id: "test-user", expires_at: Math.floor(Date.now() / 1000) + 1800, refresh_expires_at: Math.floor(Date.now() / 1000) + 604800 });

async function mockAuthentication(context: BrowserContext, initial = false) {
  const state = { valid: initial, refreshAllowed: initial, rotations: 0, logins: 0 };
  await context.route("**/api/auth/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/login")) {
      state.logins++;
      const body = route.request().postDataJSON();
      if (body.password !== "test password long enough") return route.fulfill({ status: 401, json: { detail: { code: "authentication_required" } } });
      expect(route.request().headers()["x-medi-chat-csrf"]).toBe("1");
      state.valid = state.refreshAllowed = true;
      return route.fulfill({ json: principal() });
    }
    if (path.endsWith("/logout")) {
      state.valid = state.refreshAllowed = false;
      return route.fulfill({ status: 204 });
    }
    if (path.endsWith("/refresh")) {
      state.rotations++;
      if (state.refreshAllowed) { state.valid = true; return route.fulfill({ json: principal() }); }
    }
    return state.valid ? route.fulfill({ json: principal() }) : route.fulfill({ status: 401, json: { detail: { code: "authentication_required" } } });
  });
  await context.route("**/api/attachment-imports?**", (route) => route.fulfill({ json: { items: [], total_count: 0, limit: 20, offset: 0 } }));
  return state;
}

test("login, returnTo and logout use the real UI with mocked authentication API", async ({ page, context }) => {
  const state = await mockAuthentication(context);
  await page.goto("/imports");
  await expect(page.getByRole("heading", { name: "medi-chat にログイン" })).toBeVisible();
  await page.getByLabel("ログインID", { exact: true }).fill("テスト利用者");
  await page.getByLabel("パスワード", { exact: true }).fill("wrong password long enough");
  await page.getByRole("button", { name: "ログイン", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "ログインIDまたはパスワード" })).toBeVisible();
  await page.getByLabel("パスワード", { exact: true }).fill("test password long enough");
  await page.getByRole("button", { name: "ログイン", exact: true }).click();
  await expect(page).toHaveURL(/\/imports$/);
  await expect(page.getByRole("button", { name: "ログアウト" })).toBeVisible();
  expect(state.logins).toBe(2);
  await page.getByRole("button", { name: "ログアウト" }).click();
  await expect(page.getByRole("heading", { name: "medi-chat にログイン" })).toBeVisible();
});

test("two tabs rotate once and observe logout", async ({ page, context }) => {
  const state = await mockAuthentication(context);
  state.refreshAllowed = true;
  const second = await context.newPage();
  await Promise.all([page.goto("/imports"), second.goto("/imports")]);
  await expect(page.getByRole("button", { name: "ログアウト" })).toBeVisible();
  await expect(second.getByRole("button", { name: "ログアウト" })).toBeVisible();
  expect(state.rotations).toBe(1);
  await page.getByRole("button", { name: "ログアウト" }).click();
  await expect(second.getByRole("heading", { name: "medi-chat にログイン" })).toBeVisible();
});

test("login remains usable on a narrow viewport and exposes no localStorage tokens", async ({ page, context }, testInfo) => {
  await mockAuthentication(context);
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/login?returnTo=https%3A%2F%2Fevil.invalid");
  await expect(page.getByLabel("ログインID", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "ログイン", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect(await page.evaluate(() => Object.keys(localStorage))).toEqual([]);
  await page.screenshot({ path: testInfo.outputPath("login-mobile.png"), fullPage: true });
});
