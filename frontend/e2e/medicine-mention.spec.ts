import { expect, test, type Page, type WebSocketRoute } from "@playwright/test";

interface ChatRequest {
  type: string;
  provider: string;
  model: string;
  product_yj_codes: string[];
  messages: { role: string; content: string }[];
}

const igzEntry = {
  n: "イグザレルト錠15mg",
  k: "イグザレルトジョウ15MG",
  h: "いぐざれるとじょう15mg",
  y: "3339003F5020",
  g: "リバーロキサバン錠",
  c: "内用",
};

const rokiEntry = {
  n: "ロキソニン錠60mg",
  k: "ロキソニンジョウ60MG",
  h: "ろきそにんじょう60mg",
  y: "1141007F1063",
  g: "ロキソプロフェンナトリウム水和物錠",
  c: "内用",
};

async function setupMedicineChat(
  page: Page,
  options?: {
    staticMedicines?: unknown[];
    activeMedicines?: unknown[];
    autocompleteItems?: unknown[];
  },
) {
  const requests: ChatRequest[] = [];
  let socket: WebSocketRoute | undefined;

  await page.route("**/api/medicines", (route) =>
    route.fulfill({
      json: {
        generation_id: "test-gen",
        items: options?.activeMedicines ?? [
          {
            generic_name: "リバーロキサバン錠",
            brand_names: ["イグザレルト錠15mg"],
            yj_codes: ["3339003F5020"],
            document_ids: ["doc-igz"],
            matched_aliases: [],
          },
          {
            generic_name: "ロキソプロフェンナトリウム水和物錠",
            brand_names: ["ロキソニン錠60mg"],
            yj_codes: ["1141007F1063"],
            document_ids: ["doc-roki"],
            matched_aliases: [],
          },
        ],
      },
    }),
  );

  await page.route("**/data/medicines.json", (route) =>
    route.fulfill({ json: options?.staticMedicines ?? [] }),
  );

  await page.route("**/api/medicines/autocomplete", (route) =>
    route.fulfill({
      json: {
        generation_id: "test-gen",
        items: options?.autocompleteItems ?? [igzEntry, rokiEntry],
      },
    }),
  );

  await page.routeWebSocket("**/api/ws", (ws) => {
    socket = ws;
    ws.onMessage((msg) => {
      try {
        requests.push(JSON.parse(String(msg)));
      } catch {
        // ignore non-json
      }
    });
  });

  await page.goto("/");
  await expect(page.getByText("connected", { exact: true })).toBeVisible();

  const dock = page.getByTestId("medicine-prompt-dock");
  const tier1 = page.getByTestId("tier-1-prescription");
  const tier2 = page.getByTestId("tier-2-additional");
  const input = page.getByRole("textbox", { name: "質問を入力" });
  const send = page.getByRole("button", { name: /送信|Send/ });

  return {
    requests,
    dock,
    tier1,
    tier2,
    input,
    send,
    respond(message: unknown) {
      if (!socket) throw new Error("Socket not connected");
      socket.send(JSON.stringify(message));
    },
    async disconnect() {
      if (!socket) throw new Error("Socket not connected");
      await socket.close({ code: 1001, reason: "Interruption" });
    },
  };
}

test.describe("Unit 3 & Unit 4: Medicine Mention E2E Tests", () => {
  // TC-U01: 初期表示で直上1段目に対象処方箋、2段目は「なし」
  test("TC-U01: initial view shows prescription in tier 1, and tier 2 is empty", async ({ page }) => {
    const chat = await setupMedicineChat(page);
    await expect(chat.tier1).toContainText("対象処方箋:");
    await expect(chat.tier1).toContainText("イグザレルト錠15mg");
    await expect(chat.tier2).toContainText("チャットでの追加薬:");
    await expect(chat.tier2).toContainText("なし");
  });

  // TC-U02: @ロキ で候補メニューが展開し、ロキソニンがサジェストされる
  test("TC-U02: typing @ロキ opens completion popover with suggestions", async ({ page }) => {
    const chat = await setupMedicineChat(page);
    await chat.input.focus();
    await page.keyboard.type("@ロキ");

    const option = page.getByRole("menuitem", { name: /ロキソニン/ });
    await expect(option).toBeVisible();
  });

  // TC-U03: 候補選択でトークン化され、直上2段目に追加薬が即座に表示される
  test("TC-U03: selecting completion tokenizes and reflects in tier 2 immediately", async ({ page }) => {
    const chat = await setupMedicineChat(page);
    await chat.input.focus();
    await page.keyboard.type("@ロキ");

    const option = page.getByRole("menuitem", { name: /ロキソニン/ });
    await option.click();

    // Tier 2 should now show ロキソニン錠60mg
    await expect(chat.tier2).toContainText("ロキソニン錠60mg");
  });

  // TC-U04: 直上2段目の [×] をクリックすると入力欄内のトークンが消去される
  test("TC-U04: clicking remove on tier 2 chip removes token from draft input", async ({ page }) => {
    const chat = await setupMedicineChat(page);
    await chat.input.focus();
    await page.keyboard.type("@ロキ");

    const option = page.getByRole("menuitem", { name: /ロキソニン/ });
    await option.click();

    await expect(chat.tier2).toContainText("ロキソニン錠60mg");

    // Click remove button in tier 2
    const removeBtn = chat.tier2.getByRole("button", { name: /追加薬から.*削除/ });
    await removeBtn.click();

    // Tier 2 becomes empty
    await expect(chat.tier2).toContainText("なし");
  });

  // TC-U05: 「今回はベースだけにする」で追加薬が解除される
  test("TC-U05: clicking '今回はベースだけにする' clears additional drugs", async ({ page }) => {
    const chat = await setupMedicineChat(page);
    await chat.input.focus();
    await page.keyboard.type("@ロキ");

    const option = page.getByRole("menuitem", { name: /ロキソニン/ });
    await option.click();

    await expect(chat.tier2).toContainText("ロキソニン錠60mg");

    const baseOnlyBtn = chat.tier2.getByRole("button", { name: "今回はベースだけにする" });
    await baseOnlyBtn.click();

    await expect(chat.tier2).toContainText("なし");
  });

  // TC-S01: 処方箋 A の状態で @B を含んだ質問を送信 -> payload=[A, B]、送信後も A は残る
  test("TC-S01: sending question with mention sends target [A, B] and preserves baseline A", async ({ page }) => {
    const chat = await setupMedicineChat(page);
    await chat.input.focus();
    await page.keyboard.type("併用について ");
    await page.keyboard.type("@ロキ");

    const option = page.getByRole("menuitem", { name: /ロキソニン/ });
    await option.click();

    await chat.send.click();

    await expect.poll(() => chat.requests.length).toBe(1);
    const req = chat.requests[0];
    expect(req.product_yj_codes).toEqual(["3339003F5020", "1141007F1063"]);
    expect(req.messages[0].content).toContain("@ロキソニン錠60mg");

    // Baseline prescription A remains
    await expect(chat.tier1).toContainText("イグザレルト錠15mg");
  });

  // TC-S02: 送信完了後、薬名を省略して質問を送信 -> 継続追加薬 C を引き継ぎ [A, B] を送出
  test("TC-S02: follow-up question without mentions preserves additional drug C in payload", async ({ page }) => {
    const chat = await setupMedicineChat(page);

    // Turn 1
    await chat.input.focus();
    await page.keyboard.type("@ロキ");
    const option = page.getByRole("menuitem", { name: /ロキソニン/ });
    await option.click();
    await chat.send.click();

    await expect.poll(() => chat.requests.length).toBe(1);

    // Assistant completes response
    chat.respond({ type: "text_delta", content: "ロキソニンとの併用情報です。" });
    chat.respond({ type: "text_done" });

    // Wait for response to be rendered and streaming to complete
    await expect(page.getByText("ロキソニンとの併用情報です。")).toBeVisible();

    // Turn 2: Follow-up without mentioning medicines
    await chat.input.focus();
    await page.keyboard.type("その副作用は？");
    await chat.send.click();

    await expect.poll(() => chat.requests.length).toBe(2);
    const req2 = chat.requests[1];
    expect(req2.product_yj_codes).toEqual(["3339003F5020", "1141007F1063"]);
    expect(req2.messages[req2.messages.length - 1].content).toBe("その副作用は？");
  });

  // TC-S04: 送信ボタンを高速で連打しても二重送信されない
  test("TC-S04: rapid double click does not trigger multiple sends", async ({ page }) => {
    const chat = await setupMedicineChat(page);
    await chat.input.focus();
    await page.keyboard.type("質問テキスト");

    // Click twice rapidly
    await Promise.all([
      chat.send.click(),
      chat.send.click().catch(() => {}),
    ]);

    await expect.poll(() => chat.requests.length).toBe(1);
    expect(chat.requests).toHaveLength(1);
  });

  // TC-A01: ARIA 属性 aria-label="質問を入力"
  test("TC-A01: prompt input has aria-label='質問を入力'", async ({ page }) => {
    const chat = await setupMedicineChat(page);
    await expect(chat.input).toHaveAttribute("aria-label", "質問を入力");
  });

  // TC-D01: /data/medicines.json の静的辞書にある薬も @ 補完候補に表示される
  test("TC-D01: static dictionary medicines in /data/medicines.json are available in @ mention completion even if absent from active catalog", async ({
    page,
  }) => {
    const mucostaEntry = {
      n: "ムコスタ錠100mg",
      k: "ムコスタジョウ100MG",
      h: "むこすたじょう100mg",
      y: "2329007F1023",
      g: "レバミピド錠",
      c: "内用",
    };

    const chat = await setupMedicineChat(page, {
      staticMedicines: [mucostaEntry],
    });
    await chat.input.focus();
    await page.keyboard.type("@ムコ");

    const option = page.getByRole("menuitem", { name: /ムコスタ/ });
    await expect(option).toBeVisible();
    await option.click();

    // Verify token was inserted into dock
    await expect(chat.tier2).toContainText("ムコスタ錠100mg");
  });

  // TC-W01: 選択中 baseline の YJ がカタログから消失した場合に警告を表示する
  test("TC-W01: surfaces role='alert' aria-label='選択YJの消失' when baseline YJ code is absent from active catalog", async ({
    page,
  }) => {
    const chat = await setupMedicineChat(page, {
      activeMedicines: [
        {
          generic_name: "ロキソプロフェンナトリウム水和物錠",
          brand_names: ["ロキソニン錠60mg"],
          yj_codes: ["1141007F1063"],
          document_ids: ["doc-roki"],
          matched_aliases: [],
        },
      ],
      autocompleteItems: [rokiEntry],
    });

    const alert = page.getByRole("alert", { name: "選択YJの消失" });
    await expect(alert).toBeVisible();
    await expect(alert).toContainText("3339003F5020");
    await expect(alert).toContainText("自動変更していません");
    await expect(chat.tier1).toContainText("イグザレルト錠15mg");
  });

  // TC-B01: ＋ 処方薬を追加 ボタンからポップオーバーを開いて処方箋(baseline)に薬を追加できる
  test("TC-B01: add baseline button opens popover and adds medicine to tier 1", async ({
    page,
  }) => {
    const chat = await setupMedicineChat(page);

    // Initial baseline has only イグザレルト
    await expect(chat.tier1).toContainText("イグザレルト錠15mg");
    await expect(chat.tier1).not.toContainText("ロキソニン錠60mg");

    // Click ＋ 処方薬を追加
    await page.getByRole("button", { name: "処方薬を追加" }).click();

    const dialog = page.getByRole("dialog", { name: "処方薬を選択" });
    await expect(dialog).toBeVisible();

    // Search for ロキ
    const searchInput = page.getByRole("searchbox", { name: "処方薬検索" });
    await searchInput.fill("ロキ");

    const option = page.getByRole("option", { name: /ロキソニン/ });
    await expect(option).toBeVisible();
    await option.click();

    // Dialog closes and tier 1 now contains ロキソニン
    await expect(dialog).toBeHidden();
    await expect(chat.tier1).toContainText("イグザレルト錠15mg");
    await expect(chat.tier1).toContainText("ロキソニン錠60mg");

    // Sending message includes both YJ codes
    await chat.input.fill("両方の薬について質問");
    await chat.send.click();

    expect(chat.requests).toHaveLength(1);
    expect(chat.requests[0].product_yj_codes).toEqual(
      expect.arrayContaining(["3339003F5020", "1141007F1063"]),
    );
  });

  // TC-B02: Tier 2 追加薬の ↑処方箋へ ボタンで処方箋(baseline)へ昇格できる
  test("TC-B02: promote button in tier 2 chip promotes medicine to baseline tier 1", async ({
    page,
  }) => {
    const chat = await setupMedicineChat(page);

    // Mention ロキ to put it in Tier 2
    await chat.input.focus();
    await page.keyboard.type("@ロキ");
    const option = page.getByRole("menuitem", { name: /ロキソニン/ });
    await expect(option).toBeVisible();
    await option.click();

    await expect(chat.tier2).toContainText("ロキソニン錠60mg");
    await expect(chat.tier1).not.toContainText("ロキソニン錠60mg");

    // Click ↑処方箋へ button on the Tier 2 chip
    const promoteBtn = page.getByRole("button", {
      name: "ロキソニン錠60mgを処方箋に追加",
    });
    await expect(promoteBtn).toBeVisible();
    await promoteBtn.click();

    // Tier 1 now has ロキソニン, Tier 2 becomes empty ("なし")
    await expect(chat.tier1).toContainText("ロキソニン錠60mg");
    await expect(chat.tier2).toContainText("なし");

    // Verify sending message still includes both medicines
    await chat.input.fill("昇格後の質問");
    await chat.send.click();

    expect(chat.requests).toHaveLength(1);
    expect(chat.requests[0].product_yj_codes).toEqual(
      expect.arrayContaining(["3339003F5020", "1141007F1063"]),
    );
  });

  // TC-K01: 同一 YJ コードを持つ複数医薬品（先発/後発など）のサジェスト展開時に key 重複エラーが発生しない
  test("TC-K01: medicines sharing identical YJ code render with unique keys in completions without console error", async ({
    page,
  }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        consoleErrors.push(msg.text());
      }
    });

    const isoniaEntry1 = {
      n: "イソニアジド",
      k: "イソニアジド",
      h: "いそにあじど",
      y: "6222001X1013",
      g: "",
      c: "内用",
    };
    const isoniaEntry2 = {
      n: "イスコチン原末",
      k: "イスコチンゲンマツ",
      h: "いすこちんげんまつ",
      y: "6222001X1013",
      g: "",
      c: "内用",
    };

    const chat = await setupMedicineChat(page, {
      autocompleteItems: [isoniaEntry1, isoniaEntry2],
      staticMedicines: [isoniaEntry1, isoniaEntry2],
    });

    await chat.input.focus();
    await page.keyboard.type("@イ");

    const option1 = page.getByRole("menuitem", { name: "イソニアジド" });
    const option2 = page.getByRole("menuitem", { name: "イスコチン原末" });

    await expect(option1).toBeVisible();
    await expect(option2).toBeVisible();

    // Verify no React duplicate key console error occurred
    const keyErrors = consoleErrors.filter((msg) =>
      msg.includes("Encountered two children with the same key"),
    );
    expect(keyErrors).toHaveLength(0);
  });
});
