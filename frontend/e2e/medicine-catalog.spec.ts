import { expect, test } from "@playwright/test";

for (const trigger of ["focus", "upload"] as const) {
  test(`TC110 ${trigger} refreshes groups and autocomplete without replacing selection`, async ({
    page,
  }) => {
    let current = false;
    const originalCode = "3339003F5020";
    const newCode = trigger === "focus" ? "111111111111" : originalCode;
    await page.route("**/api/medicines", (route) =>
      route.fulfill({
        json: {
          generation_id: current ? "new" : "old",
          items: [
            {
              generic_name: "成分",
              brand_names: [current ? "新版医薬品" : "旧版医薬品"],
              yj_codes: [current ? newCode : originalCode],
              document_ids: ["document"],
              matched_aliases: [],
            },
          ],
        },
      }),
    );
    await page.route("**/api/medicines/autocomplete", (route) =>
      route.fulfill({
        json: {
          generation_id: current ? "new" : "old",
          items: [
            {
              n: current ? "新版医薬品" : "旧版医薬品",
              k: "イヤクヒン",
              h: "いやくひん",
              y: current ? newCode : originalCode,
              g: "成分",
              c: "他",
            },
          ],
        },
      }),
    );
    await page.routeWebSocket("**/api/ws", () => {});
    await page.goto("/");
    await expect(
      page.getByRole("button", { name: "旧版医薬品", exact: true }),
    ).toHaveAttribute("aria-pressed", "true");
    if (trigger === "focus") {
      current = true;
      await page.evaluate(() => window.dispatchEvent(new Event("focus")));
    } else {
      await page.route("**/api/attachment-imports", (route) => {
        current = true;
        return route.fulfill({
          status: 201,
          json: {
            document_id: "document",
            source_sha256: "a".repeat(64),
            status: "registered",
            reused: false,
            validation_status: "pass",
            section_count: 1,
            search_unit_count: 1,
            products: [{ yj_code: newCode, brand_name: "新版医薬品" }],
            revisions: [],
            warnings: [],
            search_index_updated: true,
            generation_id: "new",
            registration_sequence: 2,
            active_yj_codes: [newCode],
            replaced_yj_codes: [newCode],
            deleted_version_ids: [],
            cleanup_pending: [],
            artifacts_deleted: false,
          },
        });
      });
      await page.goto("/imports");
      await page.getByLabel("XMLファイル").setInputFiles({
        name: "source.xml",
        mimeType: "text/xml",
        buffer: Buffer.from("<source/>"),
      });
      await page.getByRole("button", { name: "取り込む", exact: true }).click();
      await expect(
        page.getByText("登録済み／検索に反映済み", { exact: true }),
      ).toBeVisible();
      await page.getByRole("link", { name: "チャットへ戻る" }).click();
    }
    await expect(
      page.getByRole("button", { name: "新版医薬品", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "旧版医薬品", exact: true }),
    ).toHaveCount(0);
    await expect(
      page.getByText(`選択中: ${originalCode}`, { exact: true }),
    ).toBeVisible();
    if (trigger === "focus") {
      await expect(page.getByRole("alert", { name: "選択YJの消失" })).toContainText(
        originalCode,
      );
      await expect(
        page.getByRole("button", { name: "新版医薬品", exact: true }),
      ).toHaveAttribute("aria-pressed", "false");
    }
    await page.getByPlaceholder("確認したい内容を入力", { exact: false }).fill("新版");
    await expect(
      page.getByRole("option").filter({ hasText: "新版医薬品" }),
    ).toBeVisible();
  });
}
