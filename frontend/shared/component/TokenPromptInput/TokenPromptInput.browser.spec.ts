import { expect, test } from "@playwright/test";

test("token completion, continued typing, replacement and length limit stay controlled", async ({
  page,
}) => {
  await page.goto("/iframe.html?id=shared-tokenpromptinput--default&viewMode=story");
  const input = page.getByRole("textbox", { name: "入力内容" });
  await expect(input).toBeVisible({ timeout: 30_000 });
  await input.fill("@テスト");
  await page.getByRole("menuitem", { name: "テスト候補", exact: true }).click();
  await expect(input).toContainText("テスト候補");
  await input.press("End");
  await input.pressSequentially(" 続き");
  await page.getByRole("button", { name: "送信", exact: true }).click();
  await expect(page.getByRole("status", { name: "送信内容" })).toContainText("続き");
  await page.getByRole("button", { name: "内容を復元" }).click();
  await expect(input).toContainText("復元した内容");
  await input.fill("a".repeat(21));
  await expect(page.getByRole("button", { name: "送信", exact: true })).toBeDisabled();
  await expect(page.getByRole("alert")).toHaveText("20文字以内で入力してください");
  await input.fill("a".repeat(20));
  await expect(page.getByRole("button", { name: "送信", exact: true })).toBeEnabled();
});
