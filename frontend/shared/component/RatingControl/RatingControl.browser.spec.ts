import { expect, test } from "@playwright/test";

test("rating selection and keyboard navigation use plain values", async ({ page }) => {
  await page.goto("/iframe.html?id=shared-ratingcontrol--default&viewMode=story");
  const up = page.getByRole("radio", { name: "いいね", exact: true }),
    down = page.getByRole("radio", { name: "よくない", exact: true });
  await up.focus();
  await up.press("Enter");
  await expect(up).toHaveAttribute("aria-checked", "true");
  await up.press("ArrowRight");
  await expect(down).toBeFocused();
  await down.press("Enter");
  await expect(down).toHaveAttribute("aria-checked", "true");
  await expect(page.getByRole("status")).toHaveText("送信済み");
});
