import { expect, test } from "@playwright/test";
import { openChat } from "./helpers/chat";

test("SX-02/04: JavaScriptなしのSSRにもButtonの生成CSSが適用される", async ({
  browser,
}, testInfo) => {
  const context = await browser.newContext({
    javaScriptEnabled: false,
    baseURL: testInfo.project.use.baseURL,
  });
  try {
    const page = await context.newPage();
    await page.goto("/");
    const send = page.getByRole("button", { name: "送信", exact: true });
    await expect(send).toHaveCSS("width", "32px");
    await expect(send).toHaveCSS("height", "32px");
    await expect(send).toBeDisabled();
    await page.goto("/imports");
    await expect(page.getByLabel("XMLファイル")).toBeVisible();
    await expect(page.getByRole("button", { name: "取り込む", exact: true })).toHaveCSS(
      "background-color",
      "rgb(2, 101, 220)",
    );
  } finally {
    await context.close();
  }
});

test("SX-02/04: 初回HTMLとhydrationでSendの外観を保持する", async ({
  page,
  request,
}, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  const html = await request.get("/");
  expect(html.status()).toBe(200);
  expect(await html.text()).toContain("送信");
  const chat = await openChat(page);
  await chat.input.fill("確認する質問");
  await expect(chat.send).toBeEnabled();
  await expect(chat.send).toHaveCSS("width", "32px");
  await expect(chat.send).toHaveCSS("height", "32px");
  const appearance = await chat.send.evaluate((element) => {
    const style = getComputedStyle(element);
    return {
      background: style.backgroundColor,
      color: style.color,
      padding: style.padding,
      radius: style.borderRadius,
      fontSize: style.fontSize,
    };
  });
  // Spectrum owns the icon button's color and animated state transitions.
  // App colors/layout are covered by the visual snapshots and import button below.
  expect(appearance.background).not.toBe("rgba(0, 0, 0, 0)");
  await testInfo.attach("Send-first-paint", {
    body: await chat.send.screenshot(),
    contentType: "image/png",
  });
  await page.reload();
  await expect(chat.send).toBeVisible();
  expect(errors).toEqual([]);
  await page.goto("/imports");
  await expect(page.getByLabel("XMLファイル")).toBeVisible();
  const importButton = page.getByRole("button", { name: "取り込む", exact: true });
  await expect(importButton).toHaveCSS("background-color", "rgb(2, 101, 220)");
  await expect(importButton).toHaveCSS("padding", "8px 16px");
  await expect(importButton).toHaveCSS("border-radius", "12px");
  await expect(importButton).toHaveCSS("font-size", "13px");
  await expect(importButton).toHaveCSS("opacity", "0.5");
  expect(errors).toEqual([]);
});
