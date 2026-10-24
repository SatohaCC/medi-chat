import { expect, test } from "./helpers/test";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/attachment-imports?**", (route) =>
    route.fulfill({ json: { items: [], total_count: 0, limit: 20, offset: 0 } }),
  );
});

const result = {
  document_id: "test-document",
  source_sha256: "a".repeat(64),
  status: "registered",
  reused: false,
  validation_status: "warning",
  section_count: 3,
  search_unit_count: 3,
  products: [{ yj_code: "111111111111", brand_name: "製品A" }],
  revisions: [{ source_label: "今回", year_month: "2026-10", version: "1" }],
  warnings: [{ code: "missing_figure", reference: "figure1.gif" }],
  search_index_updated: true,
  generation_id: "gen-one",
  registration_sequence: 1,
  active_yj_codes: ["111111111111"],
  replaced_yj_codes: [],
  deleted_version_ids: [],
  cleanup_pending: [],
  artifacts_deleted: false,
};

test("original File multipart, metadata, warnings and separate selection", async ({
  page,
}) => {
  const bytes = Buffer.from("<?xml version='1.0'?><原文>Ａ①</原文>");
  let count = 0;
  await page.route("**/api/attachment-imports", async (route) => {
    count++;
    const request = route.request();
    expect(request.headers()["content-type"]).toMatch(/^multipart\/form-data; boundary=/);
    expect(request.postDataBuffer()?.includes(bytes)).toBeTruthy();
    await route.fulfill({ status: 201, json: result });
  });
  await page.goto("/imports");
  const input = page.getByLabel("XMLファイル");
  const button = page.getByRole("button", { name: "取り込む", exact: true });
  await expect(button).toBeDisabled();
  await input.setInputFiles({
    name: "<script>alert(1)</script>.xml",
    mimeType: "text/xml",
    buffer: bytes,
  });
  await button.click();
  await expect(page.getByText("登録済み／検索に反映済み", { exact: true })).toBeVisible();
  await expect(page.getByText("test-document", { exact: true })).toBeVisible();
  await expect(page.getByText("figure1.gif", { exact: false })).toBeVisible();
  await expect(page.getByText("製品A", { exact: false })).toBeVisible();
  expect(count).toBe(1);
  await input.setInputFiles({ name: "other.xml", mimeType: "text/xml", buffer: bytes });
  await expect(page.getByText("test-document", { exact: true })).not.toBeVisible();
});

test("sending disables selection and repeat requests; error allows retry", async ({
  page,
}) => {
  let count = 0;
  let release: (() => void) | undefined;
  await page.route("**/api/attachment-imports", async (route) => {
    count++;
    if (count === 1) {
      await new Promise<void>((resolve) => {
        release = resolve;
      });
      await route.fulfill({
        status: 422,
        json: { detail: { code: "invalid_xml", message: "XMLを確認してください。" } },
      });
    } else await route.fulfill({ status: 200, json: { ...result, reused: true } });
  });
  await page.goto("/imports");
  const input = page.getByLabel("XMLファイル");
  await input.setInputFiles({
    name: "input.xml",
    mimeType: "text/xml",
    buffer: Buffer.from("<source/>"),
  });
  await page.getByRole("button", { name: "取り込む", exact: true }).click();
  await expect(page.getByRole("button", { name: "送信中…" })).toBeDisabled();
  await expect(input).toBeDisabled();
  await page.keyboard.press("Enter");
  expect(count).toBe(1);
  release?.();
  await expect(page.getByRole("alert", { name: "取り込みエラー" })).toContainText(
    "XMLを確認してください。",
  );
  await page.getByRole("button", { name: "取り込む", exact: true }).click();
  await expect(
    page.getByText("同じ原本の登録情報です。新しい登録順は作成していません。", {
      exact: true,
    }),
  ).toBeVisible();
  expect(count).toBe(2);
});

for (const failure of ["server", "network"] as const) {
  test(`${failure} failure leaves retry available`, async ({ page }) => {
    let count = 0;
    await page.route("**/api/attachment-imports", async (route) => {
      count++;
      if (count > 1) return route.fulfill({ status: 201, json: result });
      if (failure === "network") return route.abort("failed");
      return route.fulfill({
        status: 500,
        json: {
          detail: { code: "storage_error", message: "保管先を確認してください。" },
        },
      });
    });
    await page.goto("/imports");
    await page.getByLabel("XMLファイル").setInputFiles({
      name: "input.xml",
      mimeType: "text/xml",
      buffer: Buffer.from("<source/>"),
    });
    const button = page.getByRole("button", { name: "取り込む", exact: true });
    await button.click();
    await expect(page.getByRole("alert", { name: "取り込みエラー" })).toBeVisible();
    await expect(
      page.getByText("登録済み／検索に反映済み", { exact: true }),
    ).not.toBeVisible();
    await expect(button).toBeEnabled();
    await button.click();
    await expect(
      page.getByText("登録済み／検索に反映済み", { exact: true }),
    ).toBeVisible();
    expect(count).toBe(2);
  });
}

for (const fixture of [
  {
    name: "pending",
    value: {
      ...result,
      status: "registered_cleanup_pending",
      cleanup_pending: [{ version_id: "old-version", reason: "lease_active" }],
    },
    text: "削除待ち",
  },
  {
    name: "partial B",
    value: {
      ...result,
      reused: true,
      active_yj_codes: ["222222222222"],
      products: [
        { yj_code: "111111111111", brand_name: "A" },
        { yj_code: "222222222222", brand_name: "B" },
      ],
    },
    text: "現在適用中のYJ: 222222222222",
  },
  {
    name: "superseded deleted",
    value: {
      ...result,
      status: "superseded",
      reused: true,
      active_yj_codes: [],
      search_index_updated: false,
      artifacts_deleted: true,
    },
    text: "旧版／現在の検索には適用されていません",
  },
]) {
  test(`TC109 ${fixture.name} registration outcome`, async ({ page }) => {
    await page.route("**/api/attachment-imports", (route) =>
      route.fulfill({ status: 200, json: fixture.value }),
    );
    await page.goto("/imports");
    await page.getByLabel("XMLファイル").setInputFiles({
      name: "source.xml",
      mimeType: "text/xml",
      buffer: Buffer.from("<source/>"),
    });
    await page.getByRole("button", { name: "取り込む", exact: true }).click();
    await expect(page.getByText(fixture.text, { exact: false })).toBeVisible();
    await expect(
      page.getByText("改訂年月ではなく、最初に登録成功した順で採用されます。", {
        exact: true,
      }),
    ).toBeVisible();
    if (fixture.name === "pending") {
      await expect(
        page.getByText("old-version: lease_active", { exact: true }),
      ).toBeVisible();
    }
  });
}
