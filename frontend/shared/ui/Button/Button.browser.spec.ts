import { expect, test } from "@playwright/test";

test("Button preserves keyboard actions, native variants and disabled state", async ({
  page,
}) => {
  const calls: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/api/")) calls.push(request.url());
  });
  await page.goto("/iframe.html?id=shared-button--states&viewMode=story");
  await page.getByRole("button", { name: "実行", exact: true }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByLabel("実行回数")).toHaveText("1");
  await expect(page.getByRole("button", { name: "無効な操作" })).toBeDisabled();
  await page.getByRole("button", { name: "Spectrumの操作" }).click();
  await page.getByRole("button", { name: "Ariaの操作" }).click();
  await expect(page.getByLabel("実行回数")).toHaveText("3");
  expect(calls).toEqual([]);
});
