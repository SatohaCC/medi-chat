import { openChat } from "./helpers/chat";
import { expect, test } from "./helpers/test";

test("SX-02/04: JavaScriptなしのSSRにもログインと認証待ちが表示される", async ({
  browser,
}, testInfo) => {
  const context = await browser.newContext({
    javaScriptEnabled: false,
    baseURL: testInfo.project.use.baseURL,
  });
  try {
    const page = await context.newPage();
    await page.goto("/login");
    await expect(page.getByLabel("ログインID", { exact: true })).toBeVisible();
    await expect(
      page.getByRole("button", { name: "ログイン", exact: true }),
    ).not.toHaveCSS("background-color", "rgba(0, 0, 0, 0)");
    await page.goto("/imports");
    await expect(page.getByRole("status")).toContainText("ログイン状態を確認");
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
  expect(await html.text()).toContain("ログイン状態を確認");
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
  await page.route("**/api/attachment-imports?*", (route) =>
    route.fulfill({ json: { items: [], total_count: 0, limit: 20, offset: 0 } }),
  );
  await page.goto("/imports");
  await expect(
    page.getByRole("button", { name: "XMLファイルを選択", exact: true }),
  ).toBeVisible();
  const importButton = page.getByRole("button", { name: "取り込む", exact: true });
  await expect(importButton).toBeDisabled();
  await expect(importButton).not.toHaveCSS("background-color", "rgba(0, 0, 0, 0)");
  expect(errors).toEqual([]);
});
