import { openChat } from "./helpers/chat";
import { visualJev, visualSource } from "./helpers/presentation";
import { expect, test } from "./helpers/test";

for (const width of [320, 390]) {
  test(`mobile ${width}: read answer, open evidence and return to answer`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 844 });
    const chat = await openChat(page);
    await expect(chat.input).toBeInViewport();
    await expect(chat.send).toBeInViewport();
    await page.getByRole("button", { name: "処方薬を追加", exact: true }).click();
    const option = page.getByRole("option", { name: /^テスト医薬品B/ });
    await expect(option).toBeInViewport();
    await option.click();
    await chat.input.fill("テストの根拠を確認");
    await chat.send.click();
    chat.respond({ type: "sources", sources: [visualSource] });
    chat.respond({ type: "jev_response", data: visualJev });
    chat.respond({ type: "text_delta", content: "モバイルで読む回答" });
    chat.respond({ type: "text_done" });
    await expect(page.getByText("モバイルで読む回答", { exact: true })).toBeVisible();
    await expect(page.getByRole("dialog")).toHaveCount(0);
    const trigger = page.getByRole("button", { name: /添付文書の根拠を表示/ });
    await trigger.click();
    const dialog = page.getByRole("dialog", { name: "添付文書の根拠", exact: true });
    await expect(dialog).toBeVisible();
    expect(await dialog.evaluate((element) => element.matches(":modal"))).toBe(true);
    const box = await dialog.boundingBox();
    expect(box?.width).toBe(width);
    expect(box?.height).toBe(844);
    const sources = dialog.getByRole("tab", { name: "添付文書の根拠", exact: true });
    await sources.focus();
    await sources.press("ArrowRight");
    await expect(
      dialog.getByRole("tab", { name: "Jev判定インスペクター" }),
    ).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
    await expect(trigger).toBeFocused();
    await page.setViewportSize({ width, height: 480 });
    await chat.input.scrollIntoViewIfNeeded();
    await expect(chat.input).toBeInViewport();
    await chat.send.scrollIntoViewIfNeeded();
    await expect(chat.send).toBeInViewport();
    await page.setViewportSize({ width, height: 844 });
    await trigger.click();
    await page.getByRole("button", { name: "根拠パネルを閉じる" }).click();
    await expect(trigger).toBeFocused();
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(width);
    await page.screenshot({ path: `../tmp/mobile-chat-${width}.png`, fullPage: true });
  });
}

test("mobile keyword search fits a 320px viewport", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 700 });
  await page.route("**/api/medicines", (route) =>
    route.fulfill({ json: { generation_id: "test", items: [] } }),
  );
  await page.goto("/search");
  await expect(page.getByRole("searchbox", { name: "検索キーワード" })).toBeInViewport();
  await expect(page.getByRole("button", { name: "検索", exact: true })).toBeInViewport();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(320);
});
