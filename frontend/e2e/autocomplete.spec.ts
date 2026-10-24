import { expect, test } from "./helpers/test";
import { openChat } from "./helpers/chat";

for (const operation of ["pointer", "Enter"] as const) {
  test(`medicine token completion preserves surrounding text (${operation})`, async ({
    page,
  }) => {
    const chat = await openChat(page);
    await chat.input.fill("前置き @テスト");
    const option = page.getByRole("menuitem", { name: "テスト医薬品B", exact: true });
    await expect(option).toBeVisible();
    if (operation === "pointer") await option.click();
    else {
      await chat.input.press("ArrowDown");
      await chat.input.press("ArrowDown");
      await chat.input.press("Enter");
    }
    await expect(page.getByTestId("tier-2-additional")).toContainText("テスト医薬品B");
    await expect(chat.input).toContainText("前置き");
    expect(chat.requests).toHaveLength(0);
    await chat.send.click();
    await expect.poll(() => chat.requests.length).toBe(1);
    expect(chat.requests[0].product_yj_codes).toEqual(["3339003F5020", "1141007F1063"]);
    expect(chat.requests[0].messages.at(-1)?.content).toContain("@テスト医薬品B");
  });
}

test("plain text does not select a medicine; Escape dismisses token completion", async ({
  page,
}) => {
  const chat = await openChat(page);
  await chat.input.fill("テスト");
  await expect(page.getByRole("menuitem")).toHaveCount(0);
  await chat.input.fill("@テスト");
  await expect(page.getByRole("menuitem")).toHaveCount(2);
  await chat.input.press("Escape");
  await expect(page.getByRole("menuitem")).toHaveCount(0);
  await expect(page.getByTestId("tier-2-additional")).toContainText("なし");
  expect(chat.requests).toHaveLength(0);
});

for (const key of ["Enter", "Tab", "Escape"]) {
  test(`synthetic composition does not submit (${key})`, async ({ page }, testInfo) => {
    const chat = await openChat(page);
    await chat.input.fill("テスト質問");
    await chat.input.dispatchEvent("compositionstart", { data: "" });
    await chat.input.dispatchEvent("compositionupdate", { data: "テスト" });
    await chat.input.dispatchEvent("keydown", { key, isComposing: true, keyCode: 229 });
    await chat.input.dispatchEvent("keyup", { key, isComposing: true, keyCode: 229 });
    await chat.input.dispatchEvent("compositionend", { data: "テスト" });
    expect(chat.requests).toHaveLength(0);
    await expect(chat.input).toContainText("テスト質問");
    await testInfo.attach("synthetic-composition", {
      body: JSON.stringify({ key, requests: chat.requests }),
      contentType: "application/json",
    });
    await chat.send.click();
    await expect.poll(() => chat.requests.length).toBe(1);
  });
}
