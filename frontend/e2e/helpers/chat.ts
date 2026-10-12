import { expect, type Page, type WebSocketRoute } from "@playwright/test";
import type { WsServerMessage } from "../../features/chat/model/chat";

interface ChatRequest {
  type: string;
  provider: string;
  model: string;
  product_yj_codes: string[];
  messages: { role: string; content: string }[];
}

export async function openChat(page: Page, options: { candidates?: boolean } = {}) {
  const requests: ChatRequest[] = [];
  let socket: WebSocketRoute | undefined;
  await page.route("**/api/medicines", (route) =>
    route.fulfill({
      json: {
        generation_id: "chat-gen",
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
  await page.route("**/api/medicines/autocomplete", (route) =>
    route.fulfill({
      json: {
        generation_id: "chat-gen",
        items:
          options.candidates === false
            ? []
            : [
                {
                  n: "テスト医薬品A",
                  k: "テストイヤクヒンA",
                  h: "てすといやくひんA",
                  y: "3339003F5020",
                  g: "テスト成分",
                  c: "他",
                },
                {
                  n: "テスト医薬品B",
                  k: "テストイヤクヒンB",
                  h: "てすといやくひんB",
                  y: "1141007F1063",
                  g: "テスト成分",
                  c: "他",
                },
              ],
      },
    }),
  );
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
