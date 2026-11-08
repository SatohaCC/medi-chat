import { expect, test } from "@playwright/test";

test("ToggleButton preserves selection, keyboard operation and disabled state", async ({
  page,
}) => {
  await page.goto("/iframe.html?id=shared-togglebutton--states&viewMode=story");
  const toggle = page.getByRole("button", { name: "オプション", exact: true });
  await toggle.focus();
  await page.keyboard.press("Space");
  await expect(toggle).toHaveAttribute("aria-pressed", "true");
  await page.keyboard.press("Space");
  await expect(toggle).toHaveAttribute("aria-pressed", "false");
  await expect(page.getByRole("button", { name: "無効な選択" })).toBeDisabled();
});
