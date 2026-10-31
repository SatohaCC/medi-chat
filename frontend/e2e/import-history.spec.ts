import { expect, test } from "./helpers/test";

const item = {
  document_id: "テスト文書",
  source_sha256: "a".repeat(64),
  filename: "テスト.xml",
  registration_sequence: 2,
  revised_at: "2026-10",
  products: [{ yj_code: "111111111111", brand_name: "テスト医薬品" }],
  active_yj_codes: ["111111111111"],
  artifacts_deleted: false,
};

test("history loads, paginates, refreshes after import, and fits mobile", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  let imported = false;
  await page.route("**/api/attachment-imports**", async (route) => {
    const url = new URL(route.request().url());
    if (route.request().method() === "POST") {
      imported = true;
      await route.fulfill({
        status: 201,
        json: {
          document_id: "テスト文書",
          source_sha256: "b".repeat(64),
          status: "registered",
          reused: false,
          validation_status: "pass",
          section_count: 1,
          search_unit_count: 1,
          products: [],
          revisions: [],
          warnings: [],
          search_index_updated: true,
          generation_id: "test-generation",
          registration_sequence: 3,
          active_yj_codes: [],
          replaced_yj_codes: [],
          deleted_version_ids: [],
          cleanup_pending: [],
          artifacts_deleted: false,
        },
      });
      return;
    }
    const offset = Number(url.searchParams.get("offset") || 0);
    await route.fulfill({
      json: {
        total_count: 21,
        limit: 20,
        offset,
        items: offset
          ? [
              {
                ...item,
                filename: null,
                artifacts_deleted: true,
                active_yj_codes: [],
                source_sha256: "c".repeat(64),
              },
            ]
          : [{ ...item, filename: imported ? "追加テスト.xml" : "テスト.xml" }],
      },
    });
  });
  await page.goto("/imports");
  const history = page.getByRole("region", { name: "取り込み済みXML" });
  await expect(
    history.getByRole("heading", { name: "テスト.xml", exact: true }),
  ).toBeVisible();
  await expect(history.getByText("検索に適用中", { exact: true })).toBeVisible();
  await history.getByRole("button", { name: "次の20件" }).click();
  await expect(history.getByText("旧版・適用なし", { exact: true })).toBeVisible();
  await expect(
    history.getByText("登録履歴のみ表示しています。", { exact: false }),
  ).toBeVisible();
  await page.locator('input[type="file"]').setInputFiles({
    name: "追加テスト.xml",
    mimeType: "text/xml",
    buffer: Buffer.from("<test/>"),
  });
  await page.getByRole("button", { name: "取り込む", exact: true }).click();
  await expect(
    history.getByRole("heading", { name: "追加テスト.xml", exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
  ).toBeTruthy();
});

test("history provides empty, error and retry states", async ({ page }) => {
  let failed = true;
  await page.route("**/api/attachment-imports**", (route) =>
    route.fulfill(
      failed
        ? { status: 500, json: {} }
        : { json: { items: [], total_count: 0, limit: 20, offset: 0 } },
    ),
  );
  await page.goto("/imports");
  const history = page.getByRole("region", { name: "取り込み済みXML" });
  await expect(history.getByRole("alert")).toBeVisible();
  failed = false;
  await history.getByRole("button", { name: "一覧を更新" }).click();
  await expect(
    history.getByText("取り込み済みのXMLはありません。", { exact: false }),
  ).toBeVisible();
});
