import { createHash } from "node:crypto";
import { expect, test } from "@playwright/test";

test("10MiB XML is sent in bounded bodies without changing original bytes", async ({
  page,
}) => {
  const original = Buffer.alloc(10 * 1024 * 1024, 120);
  const parts: Buffer[] = [];
  let declaredHash = "";
  let completed = false;
  await page.route("**/api/attachment-imports**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (request.method() === "GET") {
      await route.fulfill({ json: { items: [], total_count: 0, limit: 20, offset: 0 } });
    } else if (path.endsWith("/uploads")) {
      const body = request.postDataJSON();
      expect(body.byte_size).toBe(original.length);
      declaredHash = body.source_sha256;
      await route.fulfill({
        status: 201,
        json: {
          upload_id: "a".repeat(64),
          chunk_bytes: 3 * 1024 * 1024,
          expires_in_seconds: 3600,
        },
      });
    } else if (path.includes("/parts/")) {
      const bytes = request.postDataBuffer();
      if (!bytes) throw new Error("Missing upload body");
      expect(bytes.length).toBeLessThanOrEqual(3 * 1024 * 1024);
      parts.push(bytes);
      await route.fulfill({ status: 204 });
    } else if (path.endsWith("/complete")) {
      expect(parts).toHaveLength(4);
      expect(Buffer.concat(parts).equals(original)).toBe(true);
      expect(declaredHash).toBe(createHash("sha256").update(original).digest("hex"));
      completed = true;
      await route.fulfill({
        status: 422,
        json: { detail: { message: "テストXML検証エラー" } },
      });
    } else {
      throw new Error(`Unexpected upload request: ${path}`);
    }
  });
  await page.goto("/imports");
  await page.getByLabel("XMLファイル").setInputFiles({
    name: "テスト10MiB.xml",
    mimeType: "application/xml",
    buffer: original,
  });
  await page.getByRole("button", { name: "取り込む", exact: true }).click();
  await expect(page.getByText("テストXML検証エラー", { exact: true })).toBeVisible();
  expect(completed).toBe(true);
});

test("failed part stops upload and displays server error", async ({ page }) => {
  let completed = false;
  await page.route("**/api/attachment-imports**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (route.request().method() === "GET") {
      await route.fulfill({ json: { items: [], total_count: 0, limit: 20, offset: 0 } });
    } else if (path.endsWith("/uploads")) {
      await route.fulfill({
        status: 201,
        json: { upload_id: "b".repeat(64), chunk_bytes: 3 * 1024 * 1024 },
      });
    } else if (path.includes("/parts/")) {
      await route.fulfill({
        status: 410,
        json: { detail: { message: "取り込みを最初からやり直してください。" } },
      });
    } else {
      completed = true;
      await route.fulfill({ status: 500 });
    }
  });
  await page.goto("/imports");
  await page.getByLabel("XMLファイル").setInputFiles({
    name: "テスト中断.xml",
    mimeType: "application/xml",
    buffer: Buffer.alloc(4 * 1024 * 1024),
  });
  await page.getByRole("button", { name: "取り込む", exact: true }).click();
  await expect(
    page.getByText("取り込みを最初からやり直してください。", { exact: true }),
  ).toBeVisible();
  expect(completed).toBe(false);
});
