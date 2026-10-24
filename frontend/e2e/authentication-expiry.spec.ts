import { expect, test } from "./helpers/test";
import { openChat } from "./helpers/chat";

for (const completed of [true, false]) {
  test(`認証期限切れ時に${completed ? "完了済み回答と履歴を保持する" : "生成中の回答だけを中断する"}`, async ({
    page,
  }) => {
    const chat = await openChat(page);
    await chat.input.fill("テスト最初の質問");
    await chat.send.click();
    await expect.poll(() => chat.requests.length).toBe(1);
    chat.respond({ type: "text_delta", content: "テスト回答本文" });
    if (completed) {
      chat.respond({ type: "text_done" });
      await expect(chat.input).toBeEnabled();
    }
    const answer = page.locator('[data-message-role="assistant"]');
    await expect(answer).toContainText("テスト回答本文");
    await chat.disconnect(4001);
    await expect(page.getByText("connected", { exact: true })).toBeVisible();
    await expect(chat.input).toBeEnabled();
    if (completed) await expect(answer).not.toContainText("回答を中断しました");
    else await expect(answer).toContainText("回答を中断しました");
    expect(chat.requests).toHaveLength(1);
    await chat.input.fill("テスト次の質問");
    await chat.send.click();
    await expect.poll(() => chat.requests.length).toBe(2);
    expect(chat.requests[1].messages).toEqual([
      ...(completed
        ? [
            { role: "user", content: "テスト最初の質問" },
            { role: "assistant", content: "テスト回答本文" },
          ]
        : []),
      { role: "user", content: "テスト次の質問" },
    ]);
  });
}
