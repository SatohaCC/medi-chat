import { expect, test } from "./helpers/test";
import { openChat } from "./helpers/chat";

test("WR-007 WR-009 real hook ignores foreign terminal and duplicate send", async ({
  page,
}) => {
  const chat = await openChat(page);
  await chat.input.fill("テスト質問A");
  await chat.send.click();
  await expect.poll(() => chat.requests.length).toBe(1);
  chat.respond({ type: "text_done", request_id: "b871f25a-1eb7-4c5e-8c6e-4511dce60280" });
  await expect(chat.send).toBeDisabled();
  chat.respond({ type: "text_delta", content: "部分テスト回答" });
  await expect(page.getByText("部分テスト回答", { exact: true })).toBeVisible();
  chat.respond({ type: "text_done" });
  await chat.input.fill("テスト質問B");
  await chat.send.click();
  await expect.poll(() => chat.requests.length).toBe(2);
  chat.respond({ type: "text_done", request_id: chat.requests[0].request_id });
  await expect(chat.send).toBeDisabled();
});

test("WR-019 WR-049 stopping waits for terminal and excludes partial history", async ({
  page,
}) => {
  const chat = await openChat(page);
  await chat.input.fill("テスト質問A");
  await chat.send.click();
  await expect.poll(() => chat.requests.length).toBe(1);
  chat.respond({ type: "text_delta", content: "部分テスト回答" });
  const stop = page.getByRole("button", { name: "回答を停止", exact: true });
  await stop.focus();
  await stop.press("Enter");
  await expect(page.getByText("停止中", { exact: true })).toBeVisible();
  await expect(chat.send).toBeDisabled();
  await expect.poll(() => chat.controls.filter((c) => c.type === "abort").length).toBe(1);
  expect(chat.controls.find((c) => c.type === "abort")?.request_id).toBe(
    chat.requests[0].request_id,
  );
  chat.respond({ type: "aborted" });
  await expect(page.getByText("部分テスト回答", { exact: true })).toBeVisible();
  await chat.input.fill("テスト質問B");
  await chat.send.click();
  await expect.poll(() => chat.requests.length).toBe(2);
  expect(chat.requests[1].messages).toEqual([{ role: "user", content: "テスト質問B" }]);
});

test("WR-035 WR-038 real form queues one unsent question then sends once", async ({
  page,
}) => {
  const chat = await openChat(page);
  await page.clock.install();
  await page.clock.pauseAt(new Date(Date.now() + 1000));
  await chat.disconnect();
  await expect(page.getByText("disconnected", { exact: true })).toBeVisible();
  await expect(chat.input).toBeEnabled({ timeout: 1000 });
  await chat.input.fill("保留するテスト質問");
  await expect(chat.send).toBeEnabled({ timeout: 1000 });
  await chat.send.click();
  await expect(page.getByRole("region", { name: "未送信の保留" })).toContainText(
    "保留するテスト質問",
  );
  expect(chat.requests).toHaveLength(0);
  await expect(chat.input).toHaveText("");
  await page.clock.fastForward(6000);
  await expect.poll(() => chat.requests.length).toBe(1);
  await expect(page.getByRole("region", { name: "未送信の保留" })).toHaveCount(0);
  expect(chat.requests[0].messages).toEqual([
    { role: "user", content: "保留するテスト質問" },
  ]);
});

test("WR-041 WR-044 WR-045 cancel restores context only by explicit choice", async ({
  page,
}) => {
  const chat = await openChat(page);
  await page.clock.install();
  await page.clock.pauseAt(new Date(Date.now() + 1000));
  await chat.disconnect();
  await expect(page.getByText("disconnected", { exact: true })).toBeVisible();
  await expect(chat.input).toBeEnabled({ timeout: 1000 });
  await chat.input.fill("復元するテスト質問");
  await expect(chat.send).toBeEnabled({ timeout: 1000 });
  await chat.send.click();
  const cancel = page.getByRole("button", { name: "保留を取消", exact: true });
  await cancel.focus();
  await cancel.press("Enter");
  await expect(page.getByRole("region", { name: "未送信の質問" })).toContainText("取消");
  expect(chat.controls.filter((c) => c.type === "abort")).toHaveLength(0);
  await chat.input.fill("現在の別テストdraft");
  await page.getByRole("button", { name: "再編集", exact: true }).click();
  await page.getByRole("button", { name: "現在の入力を保持", exact: true }).click();
  await expect(chat.input).toContainText("現在の別テストdraft");
  await page.getByRole("button", { name: "再編集", exact: true }).click();
  await page.getByRole("button", { name: "元の質問に置換", exact: true }).click();
  await expect(chat.input).toContainText("復元するテスト質問");
  expect(chat.requests).toHaveLength(0);
  await page.clock.fastForward(6000);
  expect(chat.requests).toHaveLength(0);
});

test("WR-032 real hook preserves input until foreground pong", async ({ page }) => {
  const chat = await openChat(page, { respondToPing: false });
  await page.evaluate(() => {
    Object.defineProperty(document, "hidden", { configurable: true, value: true });
    document.dispatchEvent(new Event("visibilitychange"));
    Object.defineProperty(document, "hidden", { configurable: true, value: false });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await expect.poll(() => chat.controls.filter((c) => c.type === "ping").length).toBe(1);
  await chat.input.fill("前景確認中のテスト質問");
  await chat.send.click();
  expect(chat.requests).toHaveLength(0);
  await expect(chat.input).toContainText("前景確認中のテスト質問");
  chat.respond({ type: "pong", ping_id: String(chat.controls.at(-1)?.ping_id) });
  await chat.send.click();
  await expect.poll(() => chat.requests.length).toBe(1);
});

test("WR-040 WR-044 expiry is checked after delayed timer and restores empty draft", async ({
  page,
}) => {
  const chat = await openChat(page);
  await page.clock.install();
  await page.clock.pauseAt(new Date(Date.now() + 1000));
  await chat.disconnect();
  await expect(page.getByText("disconnected", { exact: true })).toBeVisible();
  await chat.input.fill("期限切れのテスト質問");
  await chat.send.click();
  await expect(page.getByRole("region", { name: "未送信の保留" })).toBeVisible();
  const time = await page.evaluate(() => Date.now());
  await page.clock.setSystemTime(new Date(time + 60000));
  await page.clock.fastForward(6000);
  await expect(page.getByRole("region", { name: "未送信の質問" })).toContainText(
    "期限切れ",
  );
  expect(chat.requests).toHaveLength(0);
  await page.getByRole("button", { name: "再編集", exact: true }).click();
  await expect(chat.input).toContainText("期限切れのテスト質問");
  expect(chat.requests).toHaveLength(0);
});

test("WR-042 authentication rejection invalidates unsent queue and blocks new acceptance", async ({
  page,
}) => {
  const chat = await openChat(page);
  await page.clock.install();
  await page.clock.pauseAt(new Date(Date.now() + 1000));
  await chat.disconnect();
  await expect(page.getByText("disconnected", { exact: true })).toBeVisible();
  await chat.input.fill("認証前のテスト保留");
  await chat.send.click();
  await page.evaluate(() =>
    Object.defineProperty(document, "hidden", { configurable: true, value: true }),
  );
  await page.clock.fastForward(6000);
  await expect(page.getByText("connected", { exact: true })).toBeVisible();
  expect(chat.requests).toHaveLength(0);
  await chat.disconnect(1008);
  await expect(page.getByRole("region", { name: "未送信の質問" })).toContainText("認証");
  await chat.input.fill("拒否後のテスト質問");
  await chat.send.click();
  expect(chat.requests).toHaveLength(0);
  await expect(chat.input).toContainText("拒否後のテスト質問");
});

test("WR-048 invalid question is retained without pending in both connection states", async ({
  page,
}) => {
  const chat = await openChat(page);
  await page.clock.install();
  await page.clock.pauseAt(new Date(Date.now() + 1000));
  for (const offline of [false, true]) {
    if (offline) {
      await chat.disconnect();
      await expect(page.getByText("disconnected", { exact: true })).toBeVisible();
    }
    await chat.input.fill("テ".repeat(4001));
    await expect(chat.send).toBeDisabled();
    await chat.input.press("Enter");
    await expect(chat.input).toContainText("テ".repeat(4001));
    expect(chat.requests).toHaveLength(0);
    await expect(page.getByRole("region", { name: "未送信の保留" })).toHaveCount(0);
  }
});

test("WR-043 pending does not survive unmount and remount", async ({ page }) => {
  const chat = await openChat(page);
  await page.clock.install();
  await page.clock.pauseAt(new Date(Date.now() + 1000));
  await chat.disconnect();
  await expect(page.getByText("disconnected", { exact: true })).toBeVisible();
  await chat.input.fill("破棄するテスト保留");
  await chat.send.click();
  await expect(page.getByRole("region", { name: "未送信の保留" })).toBeVisible();
  await page.goto("/login");
  await page.clock.fastForward(60000);
  expect(chat.requests).toHaveLength(0);
  await page.goto("/");
  await expect(page.getByText("connected", { exact: true })).toBeVisible();
  await expect(page.getByRole("region", { name: "未送信の保留" })).toHaveCount(0);
  expect(chat.requests).toHaveLength(0);
});

test("WR-047 real hook marks attempted send uncertain and requires explicit new-ID retry", async ({
  page,
}) => {
  const chat = await openChat(page);
  await page.evaluate(() => {
    const original = WebSocket.prototype.send;
    WebSocket.prototype.send = function (data) {
      const state = window as unknown as {
        failTestSend?: boolean;
        attemptedTestId?: string;
      };
      const message = typeof data === "string" ? JSON.parse(data) : null;
      if (state.failTestSend && message?.type === "message") {
        state.attemptedTestId = message.request_id;
        throw new Error("Test send attempt failure");
      }
      return original.call(this, data);
    };
  });
  await page.evaluate(() => {
    (window as unknown as { failTestSend: boolean }).failTestSend = true;
  });
  await chat.input.fill("到達不明のテスト質問");
  await chat.send.click();
  await expect(
    page.getByText(
      "回答は中断されました。未完了の回答です。送信後の到達状況は不明です。",
    ),
  ).toBeVisible();
  await expect(page.getByText("connected", { exact: true })).toBeVisible();
  expect(chat.requests).toHaveLength(0);
  await expect(chat.input).toContainText("到達不明のテスト質問");
  const oldId = await page.evaluate(() => {
    const state = window as unknown as { failTestSend: boolean; attemptedTestId: string };
    state.failTestSend = false;
    return state.attemptedTestId;
  });
  await chat.send.click();
  await expect.poll(() => chat.requests.length).toBe(1);
  expect(chat.requests[0].request_id).not.toBe(oldId);
  expect(chat.requests[0].messages).toEqual([
    { role: "user", content: "到達不明のテスト質問" },
  ]);
});
