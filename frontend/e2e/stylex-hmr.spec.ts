import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test } from "@playwright/test";
import { openChat } from "./helpers/chat";

test("SX-03: StyleXの色編集と復元が入力・選択を保持してHMRされる", async ({ page }) => {
  const chat = await openChat(page);
  await chat.input.fill("HMRで保持する質問");
  await page.getByRole("button", { name: "処方薬を追加", exact: true }).click();
  await page.getByRole("option", { name: /^テスト医薬品B/ }).click();
  const medicine = page.getByTestId("tier-1-prescription");
  const styles = resolve(
    "features/medicine-selection/components/MedicinePromptDock.styles.ts",
  );
  const original = readFileSync(styles, "utf8");
  const changed = original.replace(
    'backgroundColor: "rgba(2, 101, 220, 0.08)"',
    'backgroundColor: "#9333ea"',
  );
  expect(changed).not.toBe(original);
  const chip = page
    .getByRole("button", { name: "テスト医薬品A", exact: true })
    .locator("..");
  const initialDocument = await page.evaluate(() => {
    document.documentElement.dataset.hmrDocument = "stylex-test";
    return performance.timeOrigin;
  });
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  try {
    writeFileSync(styles, changed);
    await expect(chip).toHaveCSS("background-color", "rgb(147, 51, 234)", {
      timeout: 30_000,
    });
    await expect(chat.input).toHaveText("HMRで保持する質問");
    await expect(medicine).toContainText("テスト医薬品B");
    expect(await page.evaluate(() => performance.timeOrigin)).toBe(initialDocument);
    expect(await page.evaluate(() => document.documentElement.dataset.hmrDocument)).toBe(
      "stylex-test",
    );
    writeFileSync(styles, original);
    await expect(chip).toHaveCSS("background-color", "rgba(2, 101, 220, 0.08)", {
      timeout: 30_000,
    });
    await expect(chat.input).toHaveText("HMRで保持する質問");
    await expect(medicine).toContainText("テスト医薬品B");
    expect(await page.evaluate(() => performance.timeOrigin)).toBe(initialDocument);
    expect(await page.evaluate(() => document.documentElement.dataset.hmrDocument)).toBe(
      "stylex-test",
    );
    expect(errors).toEqual([]);
    expect(chat.requests).toHaveLength(0);
  } finally {
    writeFileSync(styles, original);
  }
});
