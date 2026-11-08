import { openChat } from "../e2e/helpers/chat";
import { visualJev, visualSource } from "../e2e/helpers/presentation";
import { expect, test } from "../e2e/helpers/test";

test("intent expansion survives tab switches and JSON retains original values", async ({
  page,
}) => {
  const chat = await openChat(page);
  await chat.input.fill("テスト質問");
  await chat.send.click();
  await expect.poll(() => chat.requests.length).toBe(1);
  chat.respond({ type: "jev_response", data: visualJev });
  chat.respond({ type: "text_delta", content: "テスト回答" });
  chat.respond({ type: "text_done" });
  await page.locator("[data-jev-toggle]").click();
  const pane = page.getByRole("complementary", { name: "添付文書の根拠引用" });
  await expect(pane.locator("[data-probability-row]")).toHaveCount(8);
  await pane.getByRole("button", { name: "全9件を表示" }).click();
  await expect(pane.locator("[data-probability-row]")).toHaveCount(9);
  await pane.getByRole("tab", { name: "詳細データ (JSON)", exact: true }).click();
  await expect(pane.locator("code")).toHaveText(JSON.stringify(visualJev, null, 2));
  await pane.getByRole("tab", { name: "判定内容", exact: true }).click();
  await expect(pane.locator("[data-probability-row]")).toHaveCount(9);
});

test("search keeps one pending request, reports failure and retries with selected filters", async ({
  page,
}) => {
  await openChat(page);
  let count = 0;
  let release: (() => void) | undefined;
  await page.route("**/api/search?**", async (route) => {
    count++;
    expect(new URL(route.request().url()).searchParams.get("q")).toBe("テスト検索");
    expect(new URL(route.request().url()).searchParams.get("expand")).toBe("true");
    expect(new URL(route.request().url()).searchParams.getAll("yj_codes")).toEqual([
      "3339003F5020",
    ]);
    if (count === 1) {
      await new Promise<void>((resolve) => {
        release = resolve;
      });
      await route.fulfill({ status: 503, json: { detail: "テスト検索失敗" } });
    } else
      await route.fulfill({
        json: {
          query: "テスト検索",
          items: [visualSource],
          expanded_keywords: ["テスト類似語"],
        },
      });
  });
  await page.goto("/search");
  await page.getByRole("button", { name: "医薬品を選んで絞り込む" }).click();
  await page.getByRole("button", { name: "テスト医薬品A", exact: true }).click();
  const expansion = page.getByRole("switch", { name: "関連する表現も検索" });
  await expansion.focus();
  await expansion.press("Space");
  await expect(expansion).toBeChecked();
  await page.getByRole("searchbox", { name: "検索キーワード" }).fill("テスト検索");
  await page.getByRole("button", { name: "検索", exact: true }).click();
  await expect.poll(() => count).toBe(1);
  await expect(page.getByRole("searchbox", { name: "検索キーワード" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "検索中…" })).toBeDisabled();
  release?.();
  await expect(page.getByRole("region", { name: "検索エラー" })).toContainText(
    "テスト検索失敗",
  );
  await page.getByRole("button", { name: "検索", exact: true }).click();
  await expect(page.getByRole("region", { name: "検索結果" })).toContainText(
    "テスト類似語",
  );
  await expect(page.getByRole("region", { name: "検索結果" })).toContainText(
    "右端の医学原文",
  );
  expect(count).toBe(2);
});
