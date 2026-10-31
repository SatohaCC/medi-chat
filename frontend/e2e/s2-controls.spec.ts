import { openChat } from "./helpers/chat";
import { expect, test } from "./helpers/test";

for (const width of [390, 1280]) {
  test(`処方薬追加のキーボードと閉じる操作 (${width})`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 });
    const chat = await openChat(page);
    await chat.input.fill("保持するテスト質問");
    const trigger = page.getByRole("button", { name: "処方薬を追加", exact: true });
    await trigger.click();
    const search = page.getByRole("searchbox", { name: "処方薬検索", exact: true });
    await expect(search).toBeFocused();
    await page.screenshot({ path: `../tmp/s2-medicine-picker-${width}.png` });
    await search.press("Escape");
    await expect(page.getByRole("dialog", { name: "処方薬を選択" })).toHaveCount(0);
    await expect(trigger).toBeFocused();
    await trigger.click();
    await search.press("ArrowDown");
    await search.press("Enter");
    await expect(page.getByTestId("tier-1-prescription")).toContainText("テスト医薬品B");
    await expect(trigger).toBeFocused();
    await expect(chat.input).toContainText("保持するテスト質問");
    const tag = page.getByRole("row", { name: /テスト医薬品B/ });
    await tag.focus();
    await tag.press("Delete");
    await expect(page.getByTestId("tier-1-prescription")).not.toContainText(
      "テスト医薬品B",
    );
    await expect(chat.input).toContainText("保持するテスト質問");
    expect(chat.requests).toHaveLength(0);
    await trigger.click();
    await page.mouse.click(8, 80);
    await expect(page.getByRole("dialog", { name: "処方薬を選択" })).toHaveCount(0);
  });
}

test("検索の消去、Enter送信、失敗時の入力保持", async ({ page }) => {
  await page.route("**/api/medicines", (route) =>
    route.fulfill({ json: { generation_id: "test", items: [] } }),
  );
  let requests = 0;
  await page.route("**/api/search?**", (route) => {
    requests++;
    return route.fulfill({ status: 503, json: { detail: "テスト検索失敗" } });
  });
  await page.goto("/search");
  const input = page.getByRole("searchbox", { name: "検索キーワード", exact: true });
  await expect(input).toBeVisible();
  await page.screenshot({ path: "../tmp/s2-keyword-search.png" });
  await input.fill("消去するテスト");
  await page.getByRole("button", { name: /クリア|Clear/ }).click();
  await expect(input).toHaveValue("");
  await input.fill("テスト検索");
  await input.press("Enter");
  await expect(
    page.getByRole("region", { name: "検索エラー" }).getByRole("alert"),
  ).toContainText("テスト検索失敗");
  await expect(input).toHaveValue("テスト検索");
  expect(requests).toBe(1);
});

test("XML選択は自動送信せず、失敗後も選択ファイルを保持する", async ({ page }) => {
  await page.route("**/api/attachment-imports?**", (route) =>
    route.fulfill({ json: { items: [], total_count: 0, limit: 20, offset: 0 } }),
  );
  let requests = 0;
  await page.route("**/api/attachment-imports", (route) => {
    requests++;
    return route.fulfill({ status: 503, json: { detail: "テスト取込失敗" } });
  });
  await page.goto("/imports");
  const chooser = page.waitForEvent("filechooser");
  await page.getByRole("button", { name: "XMLファイルを選択", exact: true }).click();
  await (await chooser).setFiles({
    name: "テスト.xml",
    mimeType: "application/xml",
    buffer: Buffer.from("<test />"),
  });
  await expect(
    page.getByText("選択したファイル: テスト.xml", { exact: true }),
  ).toBeVisible();
  expect(requests).toBe(0);
  await page.getByRole("button", { name: "取り込む", exact: true }).click();
  await expect(
    page.getByRole("region", { name: "取り込みエラー" }).getByRole("alert"),
  ).toBeVisible();
  await expect(
    page.getByText("選択したファイル: テスト.xml", { exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "取り込む", exact: true })).toBeEnabled();
  expect(requests).toBe(1);
});
