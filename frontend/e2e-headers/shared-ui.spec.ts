import { openChat } from "../e2e/helpers/chat";
import { expect, test } from "../e2e/helpers/test";

for (const width of [390, 1280]) {
  test(`shared layout and injected chat limit work in production (${width}px)`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width, height: 844 });
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    const chat = await openChat(page);
    const layout = page.locator('[data-screen="chat"]');
    await expect(layout).toHaveCSS("height", "844px");
    await expect(page.locator("header")).toHaveCSS("border-bottom-width", "1px");
    await expect(page.locator("header")).not.toHaveCSS(
      "background-color",
      "rgba(0, 0, 0, 0)",
    );
    await chat.input.fill("a".repeat(4001));
    await expect(chat.send).toBeDisabled();
    await expect(
      page.getByText("質問は4000文字以内で入力してください。", { exact: true }),
    ).toBeVisible();
    await chat.input.fill("a".repeat(4000));
    await expect(chat.send).toBeEnabled();
    await chat.input.fill("表示と操作の確認");
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(width);
    await testInfo.attach(`shared-layout-production-${width}`, {
      body: await page.screenshot(),
      contentType: "image/png",
    });
    expect(chat.requests).toHaveLength(0);
    expect(errors).toEqual([]);
  });
}
