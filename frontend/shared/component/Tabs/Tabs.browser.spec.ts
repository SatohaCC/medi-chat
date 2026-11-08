import { expect, test } from "@playwright/test";

test("Tabs preserves keyboard selection and its associated panel", async ({ page }) => {
  await page.goto("/iframe.html?id=shared-tabs--default&viewMode=story");
  await page.getByRole("tab", { name: "概要", exact: true }).focus();
  await page.keyboard.press("ArrowRight");
  const tab = page.getByRole("tab", { name: "補足", exact: true });
  await expect(tab).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(tab).toHaveAttribute("aria-selected", "true");
  await expect(page.getByRole("tabpanel")).toHaveText("補足の内容");
  const panelId = await tab.getAttribute("aria-controls");
  expect(panelId).toBeTruthy();
  await expect(page.locator(`[id="${panelId}"]`)).toHaveAttribute(
    "aria-labelledby",
    (await tab.getAttribute("id")) ?? "",
  );
});
