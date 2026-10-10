import { expect, type Page, test, type WebSocketRoute } from "@playwright/test";
import type { SourceItem, WsServerMessage } from "../app/types/chat";

interface ChatRequest {
  type: string;
  provider: string;
  model: string;
  product_yj_codes: string[];
  messages: { role: string; content: string }[];
}

const source: SourceItem = {
  unit_id: "test-section-2",
  document_id: "test-document",
  product_name: "テスト医薬品A",
  generic_name: "テスト成分",
  product_yj_codes: ["3339003F5020"],
  document_revision: { source_label: "テスト改訂", year_month: "2026-10" },
  section: { code: "2", title: "禁忌" },
  kind: "section",
  excerpt: "根拠表示のテスト用文章です。",
  references: [],
  url: "https://example.invalid/package-insert",
  retrieved_by: ["logic"],
};

async function openChat(page: Page) {
  const requests: ChatRequest[] = [];
  let socket: WebSocketRoute | undefined;
  await page.route("**/api/medicines", (route) =>
    route.fulfill({
      json: {
        items: [
          {
            generic_name: "テスト成分",
            brand_names: ["テスト医薬品A", "テスト医薬品B"],
            yj_codes: ["3339003F5020", "1141007F1063"],
            document_ids: ["test-document", "test-document-b"],
            matched_aliases: [],
          },
        ],
      },
    }),
  );
  // Keep autocomplete data deterministic too; no external API is contacted.
  await page.route("**/data/medicines.json", (route) => route.fulfill({ json: [] }));
  await page.routeWebSocket("**/api/ws", (ws) => {
    socket = ws;
    ws.onMessage((message) => requests.push(JSON.parse(String(message))));
  });
  await page.goto("/");
  await expect(page.getByText("connected", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "テスト医薬品A" })).toBeVisible();
  return {
    requests,
    input: page.getByPlaceholder("確認したい内容を入力", { exact: false }),
    send: page.getByRole("button", { name: "Send", exact: true }),
    respond(message: WsServerMessage) {
      if (!socket) throw new Error("Chat WebSocket is not connected");
      socket.send(JSON.stringify(message));
    },
    async disconnect() {
      if (!socket) throw new Error("Chat WebSocket is not connected");
      await socket.close({ code: 1001, reason: "Test connection interruption" });
    },
  };
}

test("空白の質問を送れず、回答中は追加入力・二重送信を防ぐ", async ({ page }) => {
  const chat = await openChat(page);
  await expect(chat.send).toBeDisabled();
  await chat.input.fill("   ");
  await expect(chat.send).toBeDisabled();
  expect(chat.requests).toHaveLength(0);

  await chat.input.fill("テスト質問");
  await chat.send.click();
  await expect.poll(() => chat.requests.length).toBe(1);
  await expect(chat.input).toHaveValue("");
  await expect(chat.input).toBeDisabled();
  await expect(chat.send).toBeDisabled();
  chat.respond({ type: "text_delta", content: "テスト回答です。" });
  await expect(page.locator(".message.assistant")).toContainText("テスト回答です。");
  await expect(chat.input).toBeDisabled();
  chat.respond({ type: "text_done" });
  await expect(chat.input).toBeEnabled();
  await chat.input.fill("次の質問");
  await expect(chat.send).toBeEnabled();
});

test("薬剤・モデルを指定して質問し、回答と根拠を表示して次の会話へ引き継ぐ", async ({
  page,
}) => {
  const chat = await openChat(page);
  await page.getByRole("button", { name: "テスト医薬品B" }).click();
  await page
    .locator("header")
    .getByRole("combobox")
    .selectOption("gemini:gemini-3.8-flash");
  await chat.input.fill("  根拠を確認したい  ");
  await chat.input.press("Enter");
  await expect.poll(() => chat.requests.length).toBe(1);
  expect(chat.requests[0]).toEqual({
    type: "message",
    provider: "gemini",
    model: "gemini-3.8-flash",
    product_yj_codes: ["3339003F5020", "1141007F1063"],
    messages: [{ role: "user", content: "根拠を確認したい" }],
  });
  await expect(page.locator(".message.user")).toHaveText("根拠を確認したい");
  chat.respond({ type: "retrieval_status", stage: "unavailable" });
  chat.respond({ type: "sources", sources: [source] });
  chat.respond({ type: "text_delta", content: "最初の" });
  await expect(page.locator(".message.assistant .bubble")).toContainText("最初の");
  chat.respond({ type: "text_delta", content: "テスト回答です。" });
  chat.respond({ type: "text_done" });
  await expect(page.locator(".message.assistant .bubble")).toContainText(
    "最初のテスト回答です。",
  );
  const evidence = page.getByRole("complementary", { name: "添付文書の根拠引用" });
  await expect(evidence).toContainText(source.excerpt);
  await expect(evidence).toContainText("禁忌");
  await expect(evidence.locator(`a[href="${source.url}"]`)).toBeVisible();
  await chat.input.fill("続きの質問");
  await chat.send.click();
  await expect.poll(() => chat.requests.length).toBe(2);
  expect(chat.requests[1].messages).toEqual([
    { role: "user", content: "根拠を確認したい" },
    { role: "assistant", content: "最初のテスト回答です。" },
    { role: "user", content: "続きの質問" },
  ]);
  chat.respond({ type: "text_delta", content: "続きのテスト回答です。" });
  chat.respond({ type: "text_done" });
  await expect(page.locator(".message.assistant").last()).toContainText(
    "続きのテスト回答です。",
  );
});

test("サーバーエラーを表示し、エラー回答を履歴に含めず再送信できる", async ({ page }) => {
  const chat = await openChat(page);
  await chat.input.fill("最初の質問");
  await chat.send.click();
  await expect.poll(() => chat.requests.length).toBe(1);
  chat.respond({ type: "error", content: "テスト用サーバーエラー" });
  await expect(page.locator(".message.assistant.error")).toContainText(
    "テスト用サーバーエラー",
  );
  await expect(chat.input).toBeEnabled();
  await chat.input.fill("再送信する質問");
  await chat.send.click();
  await expect.poll(() => chat.requests.length).toBe(2);
  expect(chat.requests[1].messages).toEqual([
    { role: "user", content: "最初の質問" },
    { role: "user", content: "再送信する質問" },
  ]);
  chat.respond({ type: "text_delta", content: "回復後のテスト回答です。" });
  chat.respond({ type: "text_done" });
  await expect(page.locator(".message.assistant").last()).toContainText(
    "回復後のテスト回答です。",
  );
});

test("切断された回答を中断と表示し、再接続後の履歴から未完了の会話を除く", async ({
  page,
}) => {
  const chat = await openChat(page);
  await chat.input.fill("中断される質問");
  await chat.send.click();
  await expect.poll(() => chat.requests.length).toBe(1);
  chat.respond({ type: "text_delta", content: "回答途中" });
  await expect(page.locator(".message.assistant")).toContainText("回答途中");
  await chat.disconnect();
  await expect(
    page.getByText("通信が切断され、回答が中断されました。未完了の回答です。"),
  ).toBeVisible();
  await expect(page.getByText("connected", { exact: true })).toBeVisible();
  await expect(chat.input).toBeEnabled();
  await chat.input.fill("再接続後の質問");
  await chat.send.click();
  await expect.poll(() => chat.requests.length).toBe(2);
  expect(chat.requests[1].messages).toEqual([
    { role: "user", content: "再接続後の質問" },
  ]);
  chat.respond({ type: "text_delta", content: "再接続後の回答です。" });
  chat.respond({ type: "text_done" });
  await expect(page.locator(".message.assistant").last()).toContainText(
    "再接続後の回答です。",
  );
});
