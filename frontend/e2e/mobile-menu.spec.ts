import { openChat } from "./helpers/chat";
import { expect, test } from "./helpers/test";

for (const width of [320, 390, 900]) {
  test(`Sheet navigation and model selection (${width}px)`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 });
    const chat = await openChat(page);
    const trigger = page.getByRole("button", { name: "メニューを開く" });
    await expect(page.getByRole("navigation")).toHaveCount(0);
    await trigger.focus();
    await trigger.press("Enter");
    const sheet = page.getByRole("dialog", { name: "メニュー", exact: true });
    await expect(sheet).toBeVisible();
    const waitForMenu = async () => {
      await expect
        .poll(() => sheet.evaluate((element) => element.contains(document.activeElement)))
        .toBe(true);
    };
    await waitForMenu();
    await expect(sheet.getByRole("link", { name: "チャットへ戻る" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    await sheet.getByRole("button", { name: "回答モデル" }).click();
    await page
      .getByRole("option", { name: "OpenAI (GPT-5.6 Luna)", exact: true })
      .click();
    await expect(sheet).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(sheet).toHaveCount(0);
    await expect(trigger).toBeFocused();
    await chat.input.fill("テストのモデル確認");
    await chat.send.click();
    await expect.poll(() => chat.requests[0]?.model).toBe("gpt-5.6-luna");
    await trigger.click();
    await waitForMenu();
    await page.screenshot({
      path: `../tmp/mobile-menu-settings-${width}.png`,
      fullPage: true,
    });
    await sheet.getByRole("link", { name: "キーワード検索", exact: true }).click();
    await expect(page).toHaveURL(/\/search$/);
    await expect(sheet).toHaveCount(0);
    await page.getByRole("button", { name: "メニューを開く" }).click();
    await waitForMenu();
    await expect(
      sheet.getByRole("link", { name: "キーワード検索", exact: true }),
    ).toHaveAttribute("aria-current", "page");
    await page.screenshot({ path: `../tmp/mobile-menu-${width}.png`, fullPage: true });
    await page.getByRole("button", { name: "メニューを閉じる" }).click();
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(width);
  });
}

test("desktop navigation remains visible at 901px", async ({ page }) => {
  await page.setViewportSize({ width: 901, height: 844 });
  await openChat(page);
  await expect(
    page.getByRole("navigation", { name: "メインナビゲーション" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "メニューを開く" })).toHaveCount(0);
});

test("Sheet closes from its backdrop and supports logout", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openChat(page);
  const trigger = page.getByRole("button", { name: "メニューを開く" });
  const sheet = page.getByRole("dialog", { name: "メニュー", exact: true });
  await trigger.click();
  await expect
    .poll(() => sheet.evaluate((element) => element.contains(document.activeElement)))
    .toBe(true);
  await page.mouse.click(5, 200);
  await expect(sheet).toHaveCount(0);
  await expect(trigger).toBeFocused();
  await trigger.click();
  await expect
    .poll(() => sheet.evaluate((element) => element.contains(document.activeElement)))
    .toBe(true);
  await page.route("**/api/auth/logout", (route) => route.fulfill({ status: 204 }));
  await sheet.getByRole("button", { name: "ログアウト", exact: true }).click();
  await expect(page).toHaveURL(/\/login(?:\?|$)/);
  await expect(sheet).toHaveCount(0);
});
