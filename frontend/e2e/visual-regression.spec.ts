import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { expect, type Page, type TestInfo, test } from "@playwright/test";
import { openChat } from "./helpers/chat";
import { visualImport, visualJev, visualSource } from "./helpers/presentation";

// Development chrome is outside the application visual oracle.
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    const hideDevelopmentChrome = () => {
      const style = document.createElement("style");
      style.textContent = "nextjs-portal { display: none !important; }";
      document.head.append(style);
    };
    document.addEventListener("DOMContentLoaded", hideDevelopmentChrome, { once: true });
  });
});
const geometryPath = resolve("e2e/fixtures/visual-geometry.json");
async function visualSnapshot(page: Page, testInfo: TestInfo, name: string) {
  await page.evaluate(() => document.fonts.ready);
  const regions: Record<
    string,
    { x: number; y: number; width: number; height: number } | null
  > = {};
  for (const [key, selector] of Object.entries({
    container: "[data-screen]",
    header: "header",
    messages: "main",
    form: "form",
    model: "header select, header [aria-haspopup=listbox]",
    input: "input",
    send: "form button",
    assistant: '[data-message-role="assistant"] [data-message-bubble]',
    evidence: 'aside[aria-label="添付文書の根拠引用"]',
    jev: '[data-disclosure="jev"]',
    tabs: "[role=tablist]",
    table: '[aria-label="添付文書の表（横スクロール）"]',
    importResult: '[aria-label="取り込み結果"]',
  })) {
    const target = page.locator(selector).first();
    regions[key] = (await target.count()) ? await target.boundingBox() : null;
  }
  if (process.env.MEDI_CHAT_CAPTURE_GEOMETRY === "1") {
    const baseline = existsSync(geometryPath)
      ? JSON.parse(readFileSync(geometryPath, "utf8"))
      : {};
    baseline[name] = regions;
    mkdirSync(dirname(geometryPath), { recursive: true });
    for (let attempt = 0; attempt < 5; attempt++) {
      try {
        writeFileSync(geometryPath, JSON.stringify(baseline, null, 2));
        break;
      } catch (err) {
        if (attempt === 4) throw err;
        Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 150);
      }
    }
  } else {
    const baseline = JSON.parse(readFileSync(geometryPath, "utf8"))[name];
    expect(baseline, `geometry baseline ${name}`).toBeTruthy();
    for (const [key, expected] of Object.entries(baseline) as [
      string,
      (typeof regions)[string],
    ][]) {
      if (!expected) {
        expect(regions[key], key).toBeNull();
        continue;
      }
      const actual = regions[key];
      expect(actual, key).not.toBeNull();
      if (!actual) throw new Error(`Missing ${key}`);
      for (const coordinate of ["x", "y", "width", "height"] as const)
        expect(
          Math.abs(actual[coordinate] - expected[coordinate]),
          `${name} ${key}.${coordinate}`,
        ).toBeLessThanOrEqual(2);
    }
  }
  await testInfo.attach(`geometry-${name}`, {
    body: JSON.stringify(regions),
    contentType: "application/json",
  });
  await expect(page).toHaveScreenshot(name, {
    animations: "disabled",
    ...(name.includes("stream") ? { mask: [page.locator("[data-stream-cursor]")] } : {}),
    maxDiffPixelRatio: 0.005,
    threshold: 0.2,
  });
}
const widths = [1280, 390, 899, 900, 901];
for (const width of widths) {
  test(`SX-23/V: primary screens and evidence boundary ${width}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    const chat = await openChat(page);
    await page.evaluate(() => document.fonts.ready);
    await visualSnapshot(page, testInfo, `chat-empty-${width}.png`);
    await chat.input.fill("原文を確認");
    await chat.send.click();
    chat.respond({ type: "sources", sources: [visualSource] });
    chat.respond({ type: "jev_response", data: visualJev });
    chat.respond({ type: "retrieval_status", stage: "complete" });
    chat.respond({
      type: "text_delta",
      content:
        "### 回答\n\n原文に基づく回答。\n\n- 項目\n\n`code`\n\n[安全な参照](https://example.invalid/safe)",
    });
    chat.respond({ type: "text_done" });
    await page.getByRole("button", { name: /添付文書の根拠を表示/ }).click();
    await expect(page.getByText("原文に基づく回答")).toBeVisible();
    const bubble = await page
      .locator('[data-message-role="assistant"] [data-message-bubble]')
      .boundingBox();
    const evidence = await page.getByRole("complementary").boundingBox();
    expect(bubble).not.toBeNull();
    expect(evidence).not.toBeNull();
    if (!bubble || !evidence) throw new Error("Missing evidence geometry");
    if (width <= 900) expect(evidence.y).toBeGreaterThan(bubble.y);
    else expect(evidence.x).toBeGreaterThan(bubble.x);
    await visualSnapshot(page, testInfo, `chat-complete-${width}.png`);
    await page.goto("/imports");
    await page.evaluate(() => document.fonts.ready);
    await visualSnapshot(page, testInfo, `imports-empty-${width}.png`);
  });
}
for (const width of [1280, 390]) {
  test(`V: chat states ${width}`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    const chat = await openChat(page);
    await page.getByRole("button", { name: "テスト医薬品B", exact: true }).click();
    await visualSnapshot(page, testInfo, `chat-selected-${width}.png`);
    await chat.input.fill("てす");
    await expect(page.getByRole("listbox")).toBeVisible();
    await visualSnapshot(page, testInfo, `chat-popup-${width}.png`);
    await chat.input.press("Escape");
    await chat.input.fill("原文を確認");
    await chat.send.click();
    chat.respond({ type: "text_delta", content: "固定されたストリーミング本文" });
    await expect(
      page.getByText("固定されたストリーミング本文", { exact: true }),
    ).toBeVisible();
    await visualSnapshot(page, testInfo, `chat-stream-${width}.png`);
    chat.respond({ type: "error", content: "固定されたエラー" });
    await expect(page.getByText("固定されたエラー", { exact: true })).toBeVisible();
    await visualSnapshot(page, testInfo, `chat-error-${width}.png`);
  });
  for (const state of ["busy", "success", "pending", "superseded"]) {
    test(`V: import ${state} ${width}`, async ({ page }, testInfo) => {
      await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
      await page.route("**/api/attachment-imports", async (route) => {
        if (state === "busy") return new Promise(() => {});
        await route.fulfill({
          json: {
            ...visualImport,
            ...(state === "pending"
              ? {
                  status: "registered_cleanup_pending",
                  cleanup_pending: [
                    { version_id: "old-version", reason: "lease_active" },
                  ],
                }
              : state === "superseded"
                ? { status: "superseded", artifacts_deleted: true, active_yj_codes: [] }
                : {}),
          },
        });
      });
      await page.goto("/imports");
      await page.getByLabel("XMLファイル").setInputFiles({
        name: "原本.xml",
        mimeType: "text/xml",
        buffer: Buffer.from("<source/>"),
      });
      await page.getByRole("button", { name: "取り込む", exact: true }).click();
      if (state === "busy")
        await expect(page.getByRole("button", { name: "送信中…" })).toBeDisabled();
      else await expect(page.getByRole("region", { name: "取り込み結果" })).toBeVisible();
      await visualSnapshot(page, testInfo, `imports-${state}-${width}.png`);
    });
  }
}

for (const width of [1280, 390]) {
  test(`SX-23/24 V: expanded Jev, focus and long table ${width}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    const chat = await openChat(page);
    await chat.input.fill("原文を確認");
    await chat.send.click();
    chat.respond({ type: "sources", sources: [visualSource] });
    chat.respond({ type: "jev_response", data: visualJev });
    chat.respond({ type: "retrieval_status", stage: "complete" });
    chat.respond({ type: "text_delta", content: "固定された回答" });
    chat.respond({ type: "text_done" });
    await page.getByRole("button", { name: /添付文書の根拠を表示/ }).click();
    await expect(page.getByText("固定された回答")).toBeVisible();
    const inspector = page.locator('[data-disclosure="jev"]');
    await inspector.locator("[data-disclosure-trigger]").click();
    await visualSnapshot(page, testInfo, `chat-jev-summary-${width}.png`);
    await inspector.getByRole("button", { name: "全9件を表示" }).click();
    await visualSnapshot(page, testInfo, `chat-jev-all-${width}.png`);
    await inspector.getByRole("tab", { name: "生レスポンス", exact: false }).click();
    await visualSnapshot(page, testInfo, `chat-jev-raw-${width}.png`);
    const table = page.getByRole("region", { name: "添付文書の表（横スクロール）" });
    await table.focus();
    if (width === 390) {
      const sizes = await table.evaluate((node) => ({
        scroll: node.scrollWidth,
        client: node.clientWidth,
      }));
      expect(sizes.scroll).toBeGreaterThan(sizes.client);
      await table.evaluate((node) => {
        node.scrollLeft = node.scrollWidth;
      });
      expect(await table.evaluate((node) => node.scrollLeft)).toBeGreaterThan(0);
    }
    await visualSnapshot(page, testInfo, `chat-table-focus-${width}.png`);
  });
}
