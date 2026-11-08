import { expect, test } from "@playwright/test";

test("Disclosure preserves keyboard expansion and content visibility", async ({
  page,
}) => {
  await page.goto("/iframe.html?id=shared-disclosure--states&viewMode=story");
  const disclosure = page.getByRole("button", { name: "詳細", exact: true });
  await disclosure.focus();
  await page.keyboard.press("Enter");
  await expect(disclosure).toHaveAttribute("aria-expanded", "true");
  await expect(page.getByText("任意の説明文")).toBeVisible();
  await page.keyboard.press("Enter");
  await expect(disclosure).toHaveAttribute("aria-expanded", "false");
  await expect(page.getByText("任意の説明文")).not.toBeVisible();
});
