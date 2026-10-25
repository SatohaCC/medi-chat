import { expect, type Page, test } from "./helpers/test";
import { openChat } from "./helpers/chat";

test("WR-007 WR-009 real hook ignores foreign terminal and duplicate send", async ({
  page,
}) => {
  const chat = await openChat(page);
  await chat.input.fill("テスト質問A");
  await chat.send.click();
  await expect.poll(() => chat.requests.length).toBe(1);
  chat.respond({ type: "text_done", request_id: "b871f25a-1eb7-4c5e-8c6e-4511dce60280" });
  await expect(
    page.getByRole("button", { name: "回答を停止", exact: true }),
  ).toBeEnabled();
  chat.respond({ type: "text_delta", content: "部分テスト回答" });
  await expect(page.getByText("部分テスト回答", { exact: true })).toBeVisible();
  chat.respond({ type: "text_done" });
  await chat.input.fill("テスト質問B");
  await chat.send.click();
  await expect.poll(() => chat.requests.length).toBe(2);
  chat.respond({ type: "text_done", request_id: chat.requests[0].request_id });
  await expect(
    page.getByRole("button", { name: "回答を停止", exact: true }),
  ).toBeEnabled();
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
  await stop.evaluate((button) =>
    button.setAttribute("data-action-identity", "retained"),
  );
  await expect(page.getByTestId("medicine-prompt-field").getByRole("button")).toHaveCount(
    1,
  );
  await chat.input.dispatchEvent("keydown", { key: "Enter", code: "Enter" });
  expect(chat.controls.filter((control) => control.type === "abort")).toHaveLength(0);
  await stop.focus();
  await stop.press("Enter");
  await expect(page.getByText("停止中", { exact: true })).toBeVisible();
  const stopping = page.getByRole("button", { name: "停止中", exact: true });
  await expect(stopping).toBeDisabled();
  await expect(stopping).toHaveAttribute("data-action-identity", "retained");
  await stopping.dispatchEvent("click");
  await expect.poll(() => chat.controls.filter((c) => c.type === "abort").length).toBe(1);
  expect(chat.controls.find((c) => c.type === "abort")?.request_id).toBe(
    chat.requests[0].request_id,
  );
  chat.respond({ type: "aborted" });
  await expect(page.getByText("部分テスト回答", { exact: true })).toBeVisible();
  await expect(chat.send).toHaveAttribute("data-action-identity", "retained");
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

const restoreModels = {
  current: { value: "openai:gpt-6-luna", label: "OpenAI (GPT-6 Luna)" },
  previous: { value: "openai:gpt-5.6-luna", label: "OpenAI (GPT-5.6 Luna)" },
};

async function chooseRestoreModel(page: Page, model: typeof restoreModels.current) {
  await page.getByRole("button", { name: "回答モデル" }).click();
  await page.getByRole("option", { name: model.label, exact: true }).click();
  await expect(page.getByRole("button", { name: "回答モデル" })).toContainText(
    model.label,
  );
}

async function savedRestoreQuestion(
  page: Page,
  reason: "cancelled" | "expired",
  reverse = false,
) {
  const chat = await openChat(page);
  const saved = reverse ? restoreModels.previous : restoreModels.current;
  const current = reverse ? restoreModels.current : restoreModels.previous;
  await chooseRestoreModel(page, saved);
  await chat.input.fill("復元するテスト質問 ");
  await chat.input.press("End");
  await page.keyboard.type("@テスト医薬品B");
  await page.getByRole("menuitem", { name: "テスト医薬品B", exact: true }).click();
  await page.clock.install();
  await page.clock.pauseAt(new Date(Date.now() + 1000));
  await chat.disconnect();
  await expect(page.getByText("disconnected", { exact: true })).toBeVisible();
  await page.evaluate(() => {
    const original = crypto.randomUUID.bind(crypto);
    const observed: string[] = [];
    (window as unknown as { restoreObservedIds: string[] }).restoreObservedIds = observed;
    crypto.randomUUID = () => {
      const id = original() as `${string}-${string}-${string}-${string}-${string}`;
      observed.push(id);
      return id;
    };
  });
  await chat.send.click();
  await expect(page.getByRole("region", { name: "未送信の保留" })).toBeVisible();
  const pendingId = await page.evaluate(
    () => (window as unknown as { restoreObservedIds: string[] }).restoreObservedIds[0],
  );
  if (reason === "cancelled") {
    await page.getByRole("button", { name: "保留を取消", exact: true }).click();
  } else {
    const time = await page.evaluate(() => Date.now());
    await page.clock.setSystemTime(new Date(time + 60000));
  }
  await page.clock.fastForward(6000);
  await expect(page.getByText("connected", { exact: true })).toBeVisible();
  const card = page.getByRole("region", { name: "未送信の質問" });
  const assertSaved = async () => {
    await expect(card).toContainText(reason === "cancelled" ? "取消" : "期限切れ");
    await expect(card).toContainText("復元するテスト質問");
    await expect(card).toContainText("テスト医薬品A、テスト医薬品B");
    await expect(card).toContainText(saved.value);
  };
  await assertSaved();
  await chooseRestoreModel(page, current);
  expect(chat.requests).toHaveLength(0);
  expect(chat.controls.filter((control) => control.type === "abort")).toHaveLength(0);
  const assertRestored = async () => {
    await expect(chat.input).toContainText("復元するテスト質問");
    await expect(chat.input).toContainText("テスト医薬品B");
    await expect(page.getByTestId("tier-1-prescription")).toContainText("テスト医薬品A");
    await expect(page.getByTestId("tier-1-prescription")).toContainText("テスト医薬品B");
    await expect(page.getByRole("button", { name: "回答モデル" })).toContainText(
      saved.label,
    );
    await assertSaved();
  };
  const assertSent = async (model: typeof saved, draft = false) => {
    expect(chat.requests).toHaveLength(0);
    await chat.send.click();
    await expect.poll(() => chat.requests.length).toBe(1);
    const sent = chat.requests[0];
    expect(sent.request_id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
    );
    expect(sent.request_id).not.toBe(pendingId);
    expect(pendingId).toMatch(/^[0-9a-f-]{36}$/i);
    expect(sent.provider).toBe("openai");
    expect(sent.model).toBe(model.value.split(":")[1]);
    expect(sent.product_yj_codes).toEqual(
      draft ? ["1141007F1063"] : ["3339003F5020", "1141007F1063"],
    );
    expect(sent.messages).toHaveLength(1);
    expect(sent.messages[0].role).toBe("user");
    if (draft) expect(sent.messages[0].content).toBe("現在の別テストdraft");
    else {
      expect(sent.messages[0].content).toContain("復元するテスト質問");
      expect(sent.messages[0].content).toContain("@テスト医薬品B");
    }
    await assertSaved();
  };
  return { chat, saved, current, card, assertSaved, assertRestored, assertSent };
}

test("WR-044-R1 cancelled empty draft restores saved model and token", async ({
  page,
}) => {
  const state = await savedRestoreQuestion(page, "cancelled");
  await state.card.getByRole("button", { name: "再編集", exact: true }).click();
  await expect(page.getByRole("region", { name: "再編集の確認" })).toHaveCount(0);
  await state.assertRestored();
  await state.assertSent(state.saved);
});

test("WR-044-R1 expired empty draft restores saved model and token", async ({ page }) => {
  const state = await savedRestoreQuestion(page, "expired");
  await state.card.getByRole("button", { name: "再編集", exact: true }).click();
  await expect(page.getByRole("region", { name: "再編集の確認" })).toHaveCount(0);
  await state.assertRestored();
  await state.assertSent(state.saved);
});

for (const reason of ["cancelled", "expired"] as const) {
  for (const choice of ["keep", "replace"] as const) {
    const caseId = choice === "keep" ? "WR-045-R1" : "WR-045-R2";
    test(`${caseId} ${reason} ${choice} preserves explicit model choice`, async ({
      page,
    }) => {
      const state = await savedRestoreQuestion(page, reason);
      const tier = page.getByTestId("tier-1-prescription");
      await tier.getByRole("button", { name: "全解除", exact: true }).click();
      await page.getByRole("button", { name: "処方薬を追加", exact: true }).click();
      await page.getByRole("option", { name: /^テスト医薬品B/ }).click();
      await state.chat.input.fill("現在の別テストdraft");
      const assertCurrent = async () => {
        await expect(state.chat.input).toContainText("現在の別テストdraft");
        await expect(tier).toContainText("テスト医薬品B");
        await expect(tier).not.toContainText("テスト医薬品A");
        await expect(page.getByRole("button", { name: "回答モデル" })).toContainText(
          state.current.label,
        );
        expect(state.chat.requests).toHaveLength(0);
        await state.assertSaved();
      };
      await state.card.getByRole("button", { name: "再編集", exact: true }).click();
      await expect(page.getByRole("region", { name: "再編集の確認" })).toBeVisible();
      await assertCurrent();
      await page
        .getByRole("button", {
          name: choice === "keep" ? "現在の入力を保持" : "元の質問に置換",
          exact: true,
        })
        .click();
      await expect(page.getByRole("region", { name: "再編集の確認" })).toHaveCount(0);
      if (choice === "keep") {
        await assertCurrent();
        await state.assertSent(state.current, true);
      } else {
        await state.assertRestored();
        await state.assertSent(state.saved);
      }
    });
  }
}

test("WR-045-R3 cancelled restore then deliberate model change and repeated restore", async ({
  page,
}) => {
  const state = await savedRestoreQuestion(page, "cancelled", true);
  await state.card.getByRole("button", { name: "再編集", exact: true }).click();
  await state.assertRestored();
  await chooseRestoreModel(page, state.current);
  await state.assertSent(state.current);
  state.chat.respond({ type: "text_done" });
  await expect(state.chat.input).toBeEnabled();
  await expect(state.chat.input).toHaveText("");
  await state.card.getByRole("button", { name: "再編集", exact: true }).click();
  await state.assertRestored();
  expect(state.chat.requests).toHaveLength(1);
});
