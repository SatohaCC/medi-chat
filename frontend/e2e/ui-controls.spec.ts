import { expect, test } from "@playwright/test";
import { openChat } from "./helpers/chat";
import { visualJev, visualSource } from "./helpers/presentation";

async function answer(
  page: Parameters<typeof openChat>[0],
  chat: Awaited<ReturnType<typeof openChat>>,
) {
  await chat.input.fill("原文を確認");
  await chat.send.click();
  chat.respond({ type: "sources", sources: [visualSource] });
  chat.respond({ type: "jev_response", data: visualJev });
  chat.respond({ type: "retrieval_status", stage: "complete" });
  chat.respond({ type: "text_delta", content: "固定された回答" });
  chat.respond({ type: "text_done" });
  await expect(page.getByText("Jev検索完了", { exact: true }).last()).toBeVisible();
}
test("SX-20/22: keyboard medicine selection and model agree with WS payload", async ({
  page,
}) => {
  const chat = await openChat(page);
  const b = page.getByRole("button", { name: "テスト医薬品B", exact: true });
  await b.focus();
  await b.press("Space");
  await expect(b).toHaveAttribute("aria-pressed", "true");
  await expect(b).toBeFocused();
  const model = page.getByRole("button", { name: "回答モデル" });
  await model.focus();
  await model.press("ArrowDown");
  await page
    .getByRole("option", { name: "OpenAI (GPT-5.6 Luna)", exact: true })
    .press("Enter");
  await model.press("Escape");
  await chat.input.fill("確認する質問");
  await chat.input.press("Tab");
  await expect(chat.send).toBeFocused();
  await chat.send.press("Shift+Tab");
  await expect(chat.input).toBeFocused();
  await chat.send.click();
  await expect.poll(() => chat.requests.length).toBe(1);
  expect(chat.requests[0].product_yj_codes).toEqual(["3339003F5020", "1141007F1063"]);
  expect(chat.requests[0].model).toBe("gpt-5.6-luna");
});
test("SX-21: independent disclosure and tabs for two answers", async ({
  page,
}, testInfo) => {
  const chat = await openChat(page);
  await answer(page, chat);
  await answer(page, chat);
  const inspectors = page.locator('[data-disclosure="jev"]');
  await expect(inspectors).toHaveCount(2);
  const first = inspectors.nth(0),
    second = inspectors.nth(1);
  await expect(first.getByRole("tablist")).not.toBeVisible();
  const summary = first.locator("[data-disclosure-trigger]");
  await summary.focus();
  await summary.press("Enter");
  await expect(first.getByRole("tablist")).toBeVisible();
  await expect(summary).toBeFocused();
  await first.getByRole("tab", { name: "生レスポンス", exact: false }).focus();
  await first.getByRole("tab", { name: "生レスポンス", exact: false }).press("Space");
  await expect(first.getByRole("tabpanel")).toContainText('"visual-request"');
  await expect(second.getByRole("tablist")).not.toBeVisible();
  await second.locator("[data-disclosure-trigger]").click();
  await expect(
    second.getByRole("tab", { name: "判定サマリー", exact: false }),
  ).toHaveAttribute("aria-selected", "true");
  const ids = await page
    .locator('[role="tab"]')
    .evaluateAll((nodes) => nodes.map((node) => node.id));
  expect(new Set(ids).size).toBe(ids.length);
  for (const tab of await page.getByRole("tab").all()) {
    if ((await tab.getAttribute("aria-selected")) !== "true") continue;
    const controls = await tab.getAttribute("aria-controls");
    expect(controls).toBeTruthy();
    const panel = page.locator(`[id="${controls}"]`);
    await expect(panel).toHaveCount(1);
    await expect(panel).toHaveAttribute(
      "aria-labelledby",
      (await tab.getAttribute("id")) ?? "",
    );
  }
  await testInfo.attach("tab-ids", {
    body: JSON.stringify(ids),
    contentType: "application/json",
  });
});
test("SX-24: all probabilities and raw JSON retain exact values", async ({ page }) => {
  const chat = await openChat(page);
  await answer(page, chat);
  const inspector = page.locator('[data-disclosure="jev"]');
  await inspector.locator("[data-disclosure-trigger]").click();
  await expect(inspector.getByText("確信度: 50%", { exact: true })).toBeVisible();
  await expect(inspector.locator("[data-probability-row]")).toHaveCount(8);
  await inspector.getByRole("button", { name: "全9件を表示" }).click();
  await expect(inspector.locator("[data-probability-row]")).toHaveCount(9);
  for (const [index, value] of [
    [0, 1],
    [1, 0.5],
    [8, 0],
  ] as const) {
    const row = inspector.locator("[data-probability-row]").nth(index);
    const bar = await row.locator("[data-probability-bar]").boundingBox();
    const container = await row.locator("[data-probability-track]").boundingBox();
    if (!bar || !container) throw new Error("Missing probability bar");
    expect(Math.abs(bar.width - container.width * value)).toBeLessThanOrEqual(2);
  }
  await inspector.getByRole("tab", { name: "生レスポンス", exact: false }).click();
  await expect(inspector.getByRole("tabpanel").locator("code")).toHaveText(
    JSON.stringify(visualJev, null, 2),
  );
});

for (const confidence of [0, 1]) {
  test(`SX-24: confidence boundary ${confidence}, unknown choice and missing usage`, async ({
    page,
  }) => {
    const chat = await openChat(page);
    await chat.input.fill("確認する質問");
    await chat.send.click();
    const response = {
      answers: { intent: { choice: "unknown-intent", confidence } },
      error: "固定Jevエラー",
    };
    chat.respond({ type: "jev_response", data: response });
    chat.respond({ type: "text_delta", content: "固定された回答" });
    chat.respond({ type: "text_done" });
    const inspector = page.locator('[data-disclosure="jev"]');
    await inspector.locator("[data-disclosure-trigger]").click();
    await expect(inspector).toContainText(`確信度: ${confidence * 100}%`);
    await expect(inspector).toContainText("unknown-intent");
    await expect(inspector).toContainText("Jevエラー: 固定Jevエラー");
    await expect(inspector.getByText("トークン:", { exact: false })).toHaveCount(0);
    const bar = inspector.locator("[data-confidence-meter]");
    const box = await bar.boundingBox();
    const container = await bar.locator("..").boundingBox();
    if (!box || !container) throw new Error("Missing confidence meter");
    expect(Math.abs(box.width - container.width * confidence)).toBeLessThanOrEqual(2);
  });
}
