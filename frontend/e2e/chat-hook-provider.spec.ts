import { expect, test } from "./helpers/test";
import { buildChatHookProvider } from "./helpers/build-chat-hook-provider.mjs";
import type { WsClientMessage } from "../features/chat/model/chat";

for (const order of [
  ["gemini:gemini-3.8-flash", "openai:gpt-5.6-luna"],
  ["openai:gpt-5.6-luna", "gemini:gemini-3.8-flash"],
]) {
  test(`WR-049-M2 real hook provider mapping ${order.join(" then ")}`, async ({
    page,
  }) => {
    const bundle = await buildChatHookProvider();
    await page.route("**/__chat-hook-provider", (route) =>
      route.fulfill({
        contentType: "text/html; charset=utf-8",
        body: `<!doctype html><meta charset="utf-8"><div id="harness"></div><script>${bundle.replaceAll("</script", "<\\/script")}</script>`,
      }),
    );
    const requests: WsClientMessage[] = [];
    let respond: ((data: string) => void) | undefined;
    let closed = 0;
    await page.routeWebSocket("**/api/ws", (socket) => {
      respond = (data) => socket.send(data);
      socket.onMessage((data) => {
        const message = JSON.parse(String(data));
        if (message.type === "message") requests.push(message);
        else if (message.type === "ping")
          socket.send(JSON.stringify({ type: "pong", ping_id: message.ping_id }));
      });
      socket.onClose(() => closed++);
    });
    await page.goto("/__chat-hook-provider");
    await expect(page.getByLabel("テスト接続")).toHaveText("connected");
    for (const [index, model] of order.entries()) {
      await page.getByLabel("テストモデル").selectOption(model);
      await page.getByLabel("テスト質問").fill(`テスト質問${index + 1}`);
      await page.getByRole("button", { name: "テスト送信", exact: true }).click();
      await expect.poll(() => requests.length).toBe(index + 1);
      const sent = requests[index];
      const [provider, expectedModel] = model.split(":");
      expect(sent.provider).toBe(provider);
      expect(sent.model).toBe(expectedModel);
      expect(sent.request_id).toMatch(
        /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
      );
      expect(sent.product_yj_codes).toEqual(["3339003F5020"]);
      expect(sent.messages).toEqual([
        ...(index
          ? [
              { role: "user", content: "テスト質問1" },
              { role: "assistant", content: "テスト回答1" },
            ]
          : []),
        { role: "user", content: `テスト質問${index + 1}` },
      ]);
      respond?.(
        JSON.stringify({
          type: "text_delta",
          request_id: sent.request_id,
          content: `テスト回答${index + 1}`,
        }),
      );
      respond?.(JSON.stringify({ type: "text_done", request_id: sent.request_id }));
      await expect(
        page.getByRole("button", { name: "テスト送信", exact: true }),
      ).toBeEnabled();
    }
    expect(requests[0].request_id).not.toBe(requests[1].request_id);
    await page.getByRole("button", { name: "テスト終了", exact: true }).click();
    await expect.poll(() => closed).toBe(1);
    expect(requests).toHaveLength(2);
  });
}
