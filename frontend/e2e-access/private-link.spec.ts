import { createHmac } from "node:crypto";
import { expect, test } from "@playwright/test";
import { NextRequest } from "next/server";
import { proxy } from "../proxy";

const secret = "test-access-key-for-issue-29-only-123456";

test("hosted configuration uses Secure signed cookies and fails closed without a key", () => {
  const previousSecret = process.env.APP_SECRET_KEY;
  const previousVercel = process.env.VERCEL;
  try {
    process.env.APP_SECRET_KEY = secret;
    process.env.VERCEL = "1";
    const response = proxy(new NextRequest(`https://test.vercel.app/?key=${secret}`));
    expect(response.status).toBe(303);
    expect(response.headers.get("location")).toBe("https://test.vercel.app/");
    const cookie = response.cookies.get("medi_chat_access");
    expect(cookie?.secure).toBe(true);
    expect(cookie?.httpOnly).toBe(true);
    expect(cookie?.sameSite).toBe("lax");
    expect(cookie?.maxAge).toBe(30 * 86400);
    expect(response.headers.get("set-cookie")).not.toContain(secret);
    expect(response.headers.get("referrer-policy")).toBe("no-referrer");
    expect(response.headers.get("cache-control")).toContain("no-store");
    delete process.env.APP_SECRET_KEY;
    expect(proxy(new NextRequest("https://test.vercel.app/")).status).toBe(503);
  } finally {
    if (previousSecret === undefined) delete process.env.APP_SECRET_KEY;
    else process.env.APP_SECRET_KEY = previousSecret;
    if (previousVercel === undefined) delete process.env.VERCEL;
    else process.env.VERCEL = previousVercel;
  }
});

test("anonymous pages and direct APIs are blocked", async ({ page, request }) => {
  expect((await page.goto("/"))?.status()).toBe(403);
  await expect(page.getByRole("heading", { name: "アクセスが制限されています" })).toBeVisible();
  expect((await request.post("/api/chat", { data: {} })).status()).toBe(401);
  expect((await page.goto("/?key=wrong"))?.status()).toBe(403);
});

test("private link issues an HttpOnly cookie and removes only the key", async ({ page, context }) => {
  await page.goto(`/imports?key=${secret}&keep=test`);
  await expect(page).toHaveURL("http://127.0.0.1:3120/imports?keep=test");
  await expect(page.getByLabel("XMLファイル")).toBeVisible();
  const cookie = (await context.cookies()).find((value) => value.name === "medi_chat_access");
  expect(cookie?.httpOnly).toBe(true);
  expect(cookie?.sameSite).toBe("Lax");
  expect(cookie?.path).toBe("/");
  expect(cookie?.value).not.toContain(secret);
  expect(await page.evaluate(() => document.cookie)).not.toContain("medi_chat_access");
  expect((await page.reload())?.status()).toBe(200);
});

test("expired and tampered cookies do not authorize pages", async ({ page, context }) => {
  const unsigned = `v1.1.${"a".repeat(32)}`;
  const signature = createHmac("sha256", secret).update(`medi-chat-access:${unsigned}`).digest("hex");
  for (const value of [`${unsigned}.${signature}`, "tampered"]) {
    await context.addCookies([{ name: "medi_chat_access", value, url: "http://127.0.0.1:3120" }]);
    expect((await page.goto("/imports"))?.status()).toBe(403);
  }
});
