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
    const send = page.getByRole("button", { name: "Send", exact: true });
    await expect(send).toHaveCSS("background-color", "rgb(37, 99, 235)");
    await expect(send).toHaveCSS("color", "rgb(255, 255, 255)");
    await expect(send).toHaveCSS("padding", "10px 20px");
    await expect(send).toHaveCSS("border-radius", "8px");
    await expect(send).toBeDisabled();
    await page.goto("/imports");
    await expect(page.getByLabel("XMLファイル")).toBeVisible();
    await expect(page.getByRole("button", { name: "取り込む", exact: true })).toHaveCSS(
      "background-color",
      "rgb(37, 99, 235)",
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
  expect(await html.text()).toContain("Send");
  const chat = await openChat(page);
  await chat.input.fill("確認する質問");
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
  expect(appearance).toEqual({
    background: "rgb(37, 99, 235)",
    color: "rgb(255, 255, 255)",
    padding: "10px 20px",
    radius: "8px",
    fontSize: "15px",
  });
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
  await expect(importButton).toHaveCSS("background-color", "rgb(37, 99, 235)");
  await expect(importButton).toHaveCSS("padding", "10px 20px");
  await expect(importButton).toHaveCSS("border-radius", "8px");
  await expect(importButton).toHaveCSS("font-size", "15px");
  await expect(importButton).toHaveCSS("opacity", "0.5");
  expect(errors).toEqual([]);
});
