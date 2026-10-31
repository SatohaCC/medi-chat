import { openChat } from "./helpers/chat";
import { visualJev, visualSource } from "./helpers/presentation";
import { expect, test } from "./helpers/test";

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
  await expect(page.getByText("固定された回答").last()).toBeVisible();
}
test("SX-20/22: keyboard medicine selection and model agree with WS payload", async ({
  page,
}) => {
  const chat = await openChat(page);
  await page.getByRole("button", { name: "処方薬を追加", exact: true }).click();
  const search = page.getByRole("searchbox", { name: "処方薬検索", exact: true });
  await expect(search).toBeFocused();
  await search.press("ArrowDown");
  await search.press("Enter");
  await expect(page.getByTestId("tier-1-prescription")).toContainText("テスト医薬品B");
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
test("SX-21: switches the shared evidence pane between answers and preserves accessible inspector tabs", async ({
  page,
}) => {
  const chat = await openChat(page);
  await answer(page, chat);
  await answer(page, chat);
  const toggles = page.locator("[data-jev-toggle]");
  await expect(toggles).toHaveCount(2);
  await toggles.first().focus();
  await toggles.first().press("Enter");
  const pane = page.getByRole("complementary", { name: "添付文書の根拠引用" });
  await expect(pane).toHaveCount(1);
  const raw = pane.getByRole("tab", { name: "生レスポンス", exact: false });
  await raw.focus();
  await raw.press("Space");
  await expect(pane.getByRole("tabpanel", { name: /生レスポンス/ })).toContainText(
    '"visual-request"',
  );
  const controls = await raw.getAttribute("aria-controls");
  expect(controls).toBeTruthy();
  await expect(page.locator(`[id="${controls}"]`)).toHaveAttribute(
    "aria-labelledby",
    (await raw.getAttribute("id")) ?? "",
  );
  await toggles.last().click();
  await expect(
    pane.getByRole("tab", { name: "判定サマリー", exact: false }),
  ).toHaveAttribute("aria-selected", "true");
  await expect(toggles.first()).toHaveAttribute("aria-pressed", "false");
  await expect(toggles.last()).toHaveAttribute("aria-pressed", "true");
});

test("SX-24: all probabilities and raw JSON retain exact values", async ({ page }) => {
  const chat = await openChat(page);
  await answer(page, chat);
  await page.locator("[data-jev-toggle]").click();
  const inspector = page.getByRole("complementary", { name: "添付文書の根拠引用" });
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
    await page.locator("[data-jev-toggle]").click();
    const inspector = page.getByRole("complementary", { name: "添付文書の根拠引用" });
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
