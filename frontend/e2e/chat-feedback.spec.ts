import { openChat } from "./helpers/chat";
import { expect, test } from "./helpers/test";

test("F01/F03/F05/F07/F09/F10: 回答単位の評価・変更とキーボード操作", async ({
  page,
}, testInfo) => {
  const writes: { feedback_token: string; rating: string }[] = [];
  await page.route("**/api/chat/feedback", async (route) => {
    writes.push(route.request().postDataJSON());
    expect(route.request().method()).toBe("PUT");
    expect(route.request().headers()["x-medi-chat-csrf"]).toBe("1");
    await route.fulfill({ json: { rating: writes.at(-1)?.rating } });
  });
  const chat = await openChat(page);
  await chat.input.fill("テスト質問1");
  await chat.send.click();
  await expect.poll(() => chat.requests.length).toBe(1);
  chat.respond({ type: "text_delta", content: "テスト回答1" });
  await expect(page.getByRole("radio", { name: "いいね", exact: true })).toHaveCount(0);
  chat.respond({ type: "text_done", feedback_token: "test-token-one" });
  const up = page.getByRole("radio", { name: "いいね", exact: true });
  const down = page.getByRole("radio", { name: "よくない", exact: true });
  await up.hover();
  await expect(page.getByRole("tooltip", { name: "いいね", exact: true })).toBeVisible();
  await expect(up).toHaveText("");
  await up.focus();
  await up.press("Enter");
  await expect(up).toHaveAttribute("aria-checked", "true");
  await expect(
    page.getByRole("status").filter({ hasText: "評価を送信しました" }),
  ).toHaveCSS("clip-path", "inset(50%)");
  await expect(up).toBeEnabled();
  await up.press("ArrowRight");
  await expect(down).toBeFocused();
  await down.press("Space");
  await expect(down).toHaveAttribute("aria-checked", "true");
  await expect(up).toHaveAttribute("aria-checked", "false");
  await page
    .locator('[data-message-role="assistant"]')
    .first()
    .screenshot({ path: testInfo.outputPath("feedback-redesign.png") });
  await chat.input.fill("テスト質問2");
  await chat.send.click();
  await expect.poll(() => chat.requests.length).toBe(2);
  expect(
    chat.requests[1].messages.every(
      (m) => Object.keys(m).sort().join() === "content,role",
    ),
  ).toBe(true);
  await up.click();
  await expect(up).toHaveAttribute("aria-checked", "true");
  expect(writes).toEqual([
    { feedback_token: "test-token-one", rating: "up" },
    { feedback_token: "test-token-one", rating: "down" },
    { feedback_token: "test-token-one", rating: "up" },
  ]);
  chat.respond({ type: "text_done", feedback_token: null });
});

test("F04/F06: 連打防止・失敗後の確定値維持と再試行", async ({ page }) => {
  let count = 0;
  let release: (() => void) | undefined;
  await page.route("**/api/chat/feedback", async (route) => {
    count++;
    if (count === 2) {
      await new Promise<void>((resolve) => {
        release = resolve;
      });
      await route.fulfill({ status: 503, json: { detail: "test failure" } });
    } else
      await route.fulfill({ json: { rating: route.request().postDataJSON().rating } });
  });
  const chat = await openChat(page);
  await chat.input.fill("テスト質問");
  await chat.send.click();
  await expect.poll(() => chat.requests.length).toBe(1);
  chat.respond({ type: "text_delta", content: "テスト回答" });
  chat.respond({ type: "text_done", feedback_token: "test-token" });
  const up = page.getByRole("radio", { name: "いいね", exact: true });
  const down = page.getByRole("radio", { name: "よくない", exact: true });
  await up.click();
  await expect(up).toHaveAttribute("aria-checked", "true");
  await expect(up).toBeEnabled();
  await down.click();
  await expect(down).toBeDisabled();
  await expect(up).toHaveCSS("opacity", "1");
  await expect(down).toHaveCSS("opacity", "1");
  await expect(down).toHaveAttribute("aria-checked", "true");
  await expect(up).toHaveAttribute("aria-checked", "false");
  await expect.poll(() => count).toBe(2);
  release?.();
  await expect(
    page.getByRole("alert").filter({ hasText: "評価を送信できませんでした" }),
  ).toBeVisible();
  await expect(up).toHaveAttribute("aria-checked", "true");
  await expect(down).toHaveAttribute("aria-checked", "false");
  await page.getByRole("button", { name: "評価を再試行" }).click();
  await expect(down).toHaveAttribute("aria-checked", "true");
  expect(count).toBe(3);
});

test("F02: エラー・中断・tokenなし・空回答は評価できない", async ({ page }) => {
  const chat = await openChat(page);
  for (const [index, end] of (
    [
      { type: "error", content: "テストエラー" },
      { type: "aborted" },
      { type: "text_done", feedback_token: null },
      { type: "text_done", feedback_token: "test-token" },
    ] as const
  ).entries()) {
    await chat.input.fill("テスト質問");
    await chat.send.click();
    await expect.poll(() => chat.requests.length).toBe(index + 1);
    chat.respond(end);
    await expect(chat.input).toBeEnabled();
    await expect(page.getByRole("radio", { name: "いいね", exact: true })).toHaveCount(0);
  }
});

test("F07/F11: 評価中に次の質問を送っても元の回答へ反映し、狭い画面に収まる", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  let release: (() => void) | undefined;
  await page.route("**/api/chat/feedback", async (route) => {
    await new Promise<void>((resolve) => {
      release = resolve;
    });
    await route.fulfill({ json: { rating: "up" } });
  });
  const chat = await openChat(page);
  await chat.input.fill("テスト質問1");
  await chat.send.click();
  await expect.poll(() => chat.requests.length).toBe(1);
  chat.respond({ type: "text_delta", content: "テスト回答1" });
  chat.respond({ type: "text_done", feedback_token: "test-one" });
  const up = page.getByRole("radio", { name: "いいね", exact: true });
  await up.click();
  await expect(up).toBeDisabled();
  await expect.poll(() => Boolean(release)).toBe(true);
  await chat.input.fill("テスト質問2");
  await chat.send.click();
  await expect.poll(() => chat.requests.length).toBe(2);
  release?.();
  await expect(up).toHaveAttribute("aria-checked", "true");
  chat.respond({ type: "text_delta", content: "テスト回答2" });
  chat.respond({ type: "text_done", feedback_token: "test-two" });
  const groups = page.getByRole("radiogroup", { name: "回答への評価" });
  await expect(groups).toHaveCount(2);
  await expect(
    groups.nth(1).getByRole("radio", { name: "いいね", exact: true }),
  ).toHaveAttribute("aria-checked", "false");
  const box = await groups.nth(1).boundingBox();
  expect(box && box.x >= 0 && box.x + box.width <= 390).toBeTruthy();
});

for (const status of [403, 503]) {
  test(`F06/F12: HTTP ${status}では保存済みと表示せず再試行できる`, async ({ page }) => {
    await page.route("**/api/chat/feedback", (route) =>
      route.fulfill({ status, json: { detail: "test" } }),
    );
    const chat = await openChat(page);
    await chat.input.fill("テスト質問");
    await chat.send.click();
    await expect.poll(() => chat.requests.length).toBe(1);
    chat.respond({ type: "text_delta", content: "テスト回答" });
    chat.respond({ type: "text_done", feedback_token: "test" });
    const up = page.getByRole("radio", { name: "いいね", exact: true });
    await up.click();
    await expect(
      page.getByRole("alert").filter({ hasText: "評価を送信できませんでした" }),
    ).toBeVisible();
    await expect(up).toHaveAttribute("aria-checked", "false");
    await expect(page.getByRole("button", { name: "評価を再試行" })).toBeEnabled();
  });
}

for (const reducedMotion of ["no-preference", "reduce"] as const) {
  test(`いいねのアニメーションは選択時だけ表示し、動きを減らす設定に従う (${reducedMotion})`, async ({
    page,
  }) => {
    await page.emulateMedia({ reducedMotion });
    await page.route("**/api/chat/feedback", (route) =>
      route.fulfill({ json: { rating: route.request().postDataJSON().rating } }),
    );
    const chat = await openChat(page);
    await chat.input.fill("テスト質問");
    await chat.send.click();
    await expect.poll(() => chat.requests.length).toBe(1);
    chat.respond({ type: "text_delta", content: "テスト回答" });
    chat.respond({ type: "text_done", feedback_token: "test-animation" });
    const up = page.getByRole("radio", { name: "いいね", exact: true });
    const down = page.getByRole("radio", { name: "よくない", exact: true });
    await expect(up.locator("[data-like-icon]")).toHaveCount(0);
    await up.click();
    await expect(up).toHaveAttribute("aria-checked", "true");
    const icon = up.locator("[data-like-icon]");
    if (reducedMotion === "reduce") {
      await expect(icon).toHaveCSS("animation-name", "none");
      for (const effect of await up.locator("[data-like-burst]").all())
        await expect(effect).toHaveCSS("animation-name", "none");
    } else await expect(icon).not.toHaveCSS("animation-name", "none");
    await expect(up).toBeEnabled();
    await down.click();
    await expect(down).toHaveAttribute("aria-checked", "true");
    await expect(up.locator("[data-like-icon]")).toHaveCount(0);
    await expect(down.locator("[data-like-burst]")).toHaveCount(0);
  });
}

test("再クリックで取消し、失敗時は評価を戻して取消を再試行できる", async ({ page }) => {
  const ratings: (string | null)[] = [];
  let release: (() => void) | undefined;
  await page.route("**/api/chat/feedback", async (route) => {
    const rating = route.request().postDataJSON().rating;
    ratings.push(rating);
    if (ratings.length === 2) {
      await new Promise<void>((resolve) => {
        release = resolve;
      });
      await route.fulfill({ status: 503, json: { detail: "test cancellation failure" } });
    } else await route.fulfill({ json: { rating } });
  });
  const chat = await openChat(page);
  await chat.input.fill("テスト質問");
  await chat.send.click();
  await expect.poll(() => chat.requests.length).toBe(1);
  chat.respond({ type: "text_delta", content: "テスト回答" });
  chat.respond({ type: "text_done", feedback_token: "test-cancel" });
  const up = page.getByRole("radio", { name: "いいね", exact: true });
  const down = page.getByRole("radio", { name: "よくない", exact: true });
  await up.click();
  await expect(up).toBeEnabled();
  await expect(up).toHaveAttribute("aria-checked", "true");
  await up.click();
  await expect(up).toHaveAttribute("aria-checked", "false");
  await expect(down).toHaveAttribute("aria-checked", "false");
  await expect(up).toHaveCSS("opacity", "1");
  await expect(down).toHaveCSS("opacity", "1");
  await expect.poll(() => ratings.length).toBe(2);
  release?.();
  await expect(
    page.getByRole("alert").filter({ hasText: "評価を送信できませんでした" }),
  ).toBeVisible();
  await expect(up).toHaveAttribute("aria-checked", "true");
  await page.getByRole("button", { name: "評価を再試行" }).click();
  await expect(up).toBeEnabled();
  await expect(up).toHaveAttribute("aria-checked", "false");
  expect(ratings).toEqual(["up", null, null]);
  await down.click();
  await expect(down).toBeEnabled();
  await expect(down).toHaveAttribute("aria-checked", "true");
  await down.click();
  await expect(down).toBeEnabled();
  await expect(down).toHaveAttribute("aria-checked", "false");
  expect(ratings).toEqual(["up", null, null, "down", null]);
});
