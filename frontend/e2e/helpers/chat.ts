import { expect, type Page, type WebSocketRoute } from "@playwright/test";
import type { WsServerMessage } from "../../features/chat/model/chat";

type MockResponse<E = WsServerMessage> = E extends { request_id: string }
  ? Omit<E, "request_id"> & { request_id?: string }
  : E;

interface ChatRequest {
  type: string;
  request_id: string;
  provider: string;
  model: string;
  product_yj_codes: string[];
  messages: { role: string; content: string }[];
}

export async function openChat(
  page: Page,
  options: { candidates?: boolean; respondToPing?: boolean } = {},
) {
  const requests: ChatRequest[] = [];
  const controls: { type: string; request_id?: string; ping_id?: string }[] = [];
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
  await page.route("**/data/medicines.json", (route) => route.fulfill({ json: [] }));
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
    ws.onMessage((message) => {
      const data = JSON.parse(String(message));
      if (data.type === "message") requests.push(data);
      else {
        controls.push(data);
        if (data.type === "ping" && options.respondToPing !== false)
          ws.send(JSON.stringify({ type: "pong", ping_id: data.ping_id }));
      }
    });
  });
  await page.goto("/");
  const menu = page.getByRole("button", { name: "メニューを開く" });
  if ((page.viewportSize()?.width ?? 1280) <= 900) {
    await expect(menu).toBeVisible();
    await menu.click();
    await expect(page.getByText("connected", { exact: true })).toBeVisible();
    await expect
      .poll(() =>
        page
          .getByRole("dialog", { name: "メニュー", exact: true })
          .evaluate((element) => element.contains(document.activeElement)),
      )
      .toBe(true);
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog", { name: "メニュー", exact: true })).toHaveCount(
      0,
    );
  } else await expect(page.getByText("connected", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "テスト医薬品A", exact: true }),
  ).toBeVisible();
  return {
    requests,
    controls,
    input: page.getByRole("textbox", { name: "質問を入力" }),
    send: page.getByRole("button", { name: /送信|Send/ }),
    respond(message: MockResponse) {
      if (!socket) throw new Error("Chat WebSocket is not connected");
      socket.send(
        JSON.stringify({ request_id: requests.at(-1)?.request_id, ...message }),
      );
    },
    async disconnect(code = 1001) {
      if (!socket) throw new Error("Chat WebSocket is not connected");
      await socket.close({ code, reason: "Test connection interruption" });
    },
  };
}
