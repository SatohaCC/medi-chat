import { expect, test } from "@playwright/test";

for (const width of [390, 1280]) {
  for (const withControls of [false, true]) {
    test(`Header renders connection status with controls=${withControls} (${width}px)`, async ({
      page,
    }) => {
      await page.setViewportSize({ width, height: 844 });
      const story = withControls
        ? "connection-status-with-controls"
        : "connection-status-only";
      await page.goto(`/iframe.html?id=shared-header--${story}&viewMode=story`);
      await expect(
        page.getByRole("heading", { name: "接続状態のヘッダー" }),
      ).toBeVisible();
      if (width < 901) await page.getByRole("button", { name: "メニューを開く" }).click();
      const region =
        width < 901
          ? page.getByRole("dialog", { name: "メニュー", exact: true })
          : page.getByRole("banner");
      await expect(region.getByRole("status")).toHaveText("接続済み");
      await expect(region.getByRole("status")).toBeVisible();
      await expect(region.getByRole("status")).toHaveCount(1);
      if (withControls)
        await expect(region.getByText("表示オプション", { exact: true })).toBeVisible();
      else
        await expect(region.getByText("表示オプション", { exact: true })).toHaveCount(0);
    });
  }

  test(`shared Header supports injected navigation and focus (${width}px)`, async ({
    page,
  }) => {
    const calls: string[] = [];
    page.on("request", (request) => {
      if (request.url().includes("/api/")) calls.push(request.url());
    });
    await page.setViewportSize({ width, height: 844 });
    await page.goto("/iframe.html?id=shared-header--workspace&viewMode=story");
    await expect(page.getByRole("heading", { name: "Example workspace" })).toBeVisible();
    if (width < 901) {
      const trigger = page.getByRole("button", { name: "メニューを開く" });
      await trigger.click();
      const dialog = page.getByRole("dialog", { name: "メニュー", exact: true });
      await expect(dialog).toBeVisible();
      await expect
        .poll(() =>
          dialog.evaluate((element) => element.contains(document.activeElement)),
        )
        .toBe(true);
      await page.keyboard.press("Escape");
      await expect(dialog).toHaveCount(0);
      await expect(trigger).toBeFocused();
      await trigger.click();
      await dialog.getByRole("link", { name: "詳細", exact: true }).click();
      await expect(dialog).toHaveCount(0);
    } else {
      await expect(page.getByRole("navigation", { name: "ページ一覧" })).toBeVisible();
    }
    await expect(page.locator("mark")).toHaveText("強調");
    expect(calls).toEqual([]);
  });
}
