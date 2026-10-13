import { expect, test } from "@playwright/test";
import type { SourceItem } from "../features/chat/model/chat";
import { zeroSelectionBundle } from "./harness/bundle";
import { openChat } from "./helpers/chat";
import { visualSource } from "./helpers/presentation";

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

for (const operation of ["pointer", "Enter", "Space", "input Enter"] as const) {
  test(`SX-05: ${operation}で一操作につき一回だけ送信する`, async ({ page }) => {
    const chat = await openChat(page);
    await chat.input.fill("  確認する質問  ");
    if (operation === "pointer") await chat.send.click();
    else if (operation === "input Enter") await chat.input.press("Enter");
    else {
      await chat.send.focus();
      await chat.send.press(operation);
    }
    await expect.poll(() => chat.requests.length).toBe(1);
    expect(chat.requests[0].messages).toEqual([
      { role: "user", content: "確認する質問" },
    ]);
    expect(chat.requests[0].product_yj_codes).toEqual(["3339003F5020"]);
    await expect(chat.send).toBeDisabled();
    await page.keyboard.press("Enter");
    await page.keyboard.press("Space");
    expect(chat.requests).toHaveLength(1);
    chat.respond({ type: "text_done" });
    await expect(chat.input).toBeEnabled();
    expect(chat.requests).toHaveLength(1);
  });
}

test("SX-R07 / SX-06: 実formとhookで薬剤0の送信禁止と復帰を観測する", async ({
  page,
}) => {
  const bundle = await zeroSelectionBundle();
  await page.route("**/zero-selection-harness", (route) =>
    route.fulfill({
      contentType: "text/html",
      body: '<!doctype html><html lang="ja"><body><div id="root"></div><script src="/zero-selection-harness.js"></script></body></html>',
    }),
  );
  await page.route("**/zero-selection-harness.js", (route) =>
    route.fulfill({
      contentType: "application/javascript",
      body: bundle,
    }),
  );
  const chat = await openChat(page);
  await page.goto("/zero-selection-harness");
  await expect(page.getByText("connected", { exact: true })).toBeVisible();
  await chat.input.fill("確認する質問");
  await expect(chat.send).toBeDisabled();
  await chat.input.press("Enter");
  expect(chat.requests).toHaveLength(0);
  await page.getByRole("button", { name: "選択を復帰" }).click();
  await expect(chat.send).toBeEnabled();
  await chat.input.press("Enter");
  await expect.poll(() => chat.requests.length).toBe(1);
  expect(chat.requests[0].product_yj_codes).toEqual(["3339003F5020"]);
});

test("SX-06: 切断中は送信できず、復帰後に再開する", async ({ page }) => {
  const chat = await openChat(page);
  await chat.input.fill("確認する質問");
  await chat.disconnect();
  await expect(chat.input).toBeDisabled();
  await expect(chat.send).toBeDisabled();
  await page.keyboard.press("Enter");
  expect(chat.requests).toHaveLength(0);
  await expect(page.getByText("connected", { exact: true })).toBeVisible();
  await expect(chat.input).toBeEnabled();
  await chat.send.click();
  await expect.poll(() => chat.requests.length).toBe(1);
  chat.respond({ type: "text_done" });
});

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
  await expect(page.locator('[data-message-role="assistant"]')).toContainText(
    "テスト回答です。",
  );
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
  await page.getByRole("button", { name: "回答モデル" }).click();
  await page.getByRole("option", { name: "Google (Gemini 3.8 Flash)" }).click();
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
  await expect(page.locator('[data-message-role="user"]')).toHaveText("根拠を確認したい");
  chat.respond({ type: "retrieval_status", stage: "unavailable" });
  chat.respond({ type: "sources", sources: [source] });
  chat.respond({ type: "text_delta", content: "最初の" });
  await expect(
    page.locator('[data-message-role="assistant"] [data-message-bubble]'),
  ).toContainText("最初の");
  chat.respond({ type: "text_delta", content: "テスト回答です。" });
  chat.respond({ type: "text_done" });
  await expect(
    page.locator('[data-message-role="assistant"] [data-message-bubble]'),
  ).toContainText("最初のテスト回答です。");
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
  await expect(page.locator('[data-message-role="assistant"]').last()).toContainText(
    "続きのテスト回答です。",
  );
});

test("サーバーエラーを表示し、エラー回答を履歴に含めず再送信できる", async ({ page }) => {
  const chat = await openChat(page);
  await chat.input.fill("最初の質問");
  await chat.send.click();
  await expect.poll(() => chat.requests.length).toBe(1);
  chat.respond({ type: "error", content: "テスト用サーバーエラー" });
  await expect(
    page.locator('[data-message-role="assistant"][data-message-error="true"]'),
  ).toContainText("テスト用サーバーエラー");
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
  await expect(page.locator('[data-message-role="assistant"]').last()).toContainText(
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
  await expect(page.locator('[data-message-role="assistant"]')).toContainText("回答途中");
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
  await expect(page.locator('[data-message-role="assistant"]').last()).toContainText(
    "再接続後の回答です。",
  );
});

test("SX-26/27: section/all/zero selection, references and safe Markdown remain", async ({
  page,
}) => {
  const chat = await openChat(page);
  await chat.input.fill("原文を確認");
  await chat.send.click();
  const second = {
    ...visualSource,
    unit_id: "second-unit",
    section: { code: "2", title: "禁忌" },
    excerpt: "禁忌の正文",
    retrieved_by: ["logic"] as const,
  };
  chat.respond({
    type: "sources",
    sources: [visualSource, { ...second, retrieved_by: ["logic"] }],
  });
  chat.respond({ type: "retrieval_status", stage: "complete" });
  chat.respond({
    type: "text_delta",
    content:
      "### Markdownの見出し\n\n- 原文の一覧\n\n```text\n安全なcode\n```\n\n|列|値|\n|---|---|\n|正文|保持|\n\n[安全なURL](https://example.invalid/safe) [危険なURL](javascript:alert(1))\n\n<script>alert(2)</script>",
  });
  chat.respond({ type: "text_done" });
  const evidence = page.getByRole("complementary");
  await expect(evidence).toContainText("合計：2件");
  await evidence.getByRole("button", { name: "[2] 禁忌 (1)", exact: true }).click();
  await expect(evidence.getByText("禁忌の正文", { exact: true })).toBeVisible();
  await expect(evidence.getByRole("heading", { name: "原文の見出し" })).not.toBeVisible();
  await evidence.getByRole("button", { name: "すべて (2)", exact: true }).click();
  await expect(evidence.getByRole("heading", { name: "原文の見出し" })).toBeVisible();
  await expect(
    evidence.locator('a[href="https://example.invalid/reference#2.12"]'),
  ).toHaveCount(2);
  const safe = page.getByRole("link", { name: "安全なURL", exact: true });
  await expect(safe).toHaveAttribute("href", "https://example.invalid/safe");
  await expect(safe).toHaveAttribute("target", "_blank");
  await expect(safe).toHaveAttribute("rel", "noopener noreferrer");
  await expect(page.locator('a[href^="javascript:"]')).toHaveCount(0);
  await expect(page.locator("main script")).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: "Markdownの見出し", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("安全なcode", { exact: true })).toBeVisible();
  await chat.input.fill("根拠0");
  await chat.send.click();
  chat.respond({ type: "sources", sources: [] });
  chat.respond({ type: "retrieval_status", stage: "complete" });
  chat.respond({ type: "text_delta", content: "根拠0の回答" });
  chat.respond({ type: "text_done" });
  await expect(page.getByRole("complementary").last()).toContainText("合計：0件");
});

test("チャット送信時に、送信したユーザー質問が画面上部にスクロールする", async ({
  page,
}) => {
  const chat = await openChat(page);
  await chat.input.fill("最初の長い質問");
  await chat.send.click();
  chat.respond({ type: "sources", sources: [source] });
  chat.respond({
    type: "text_delta",
    content: "行の内容\n\n".repeat(30),
  });
  chat.respond({ type: "text_done" });

  await chat.input.fill("2回目の質問");
  await chat.send.click();

  const secondUser = page.locator('[data-message-role="user"]').nth(1);
  const main = page.locator("main");
  await expect(secondUser).toBeVisible();

  await expect
    .poll(async () => {
      const mainBox = await main.boundingBox();
      const userBox = await secondUser.boundingBox();
      if (!mainBox || !userBox) return -1;
      return Math.abs(userBox.y - mainBox.y);
    })
    .toBeLessThan(60);
});
