import { expect, test } from "@playwright/test";

for (const path of ["/", "/login", "/imports", "/search", "/guide"]) {
  for (const cookie of ["", "medi_chat_access_token=test-token"]) {
    test(`${path} keeps production response policy with ${cookie ? "a cookie" : "no cookie"}`, async ({ request }) => {
      for (const method of ["GET", "HEAD"]) {
        const response = await request.fetch(path, { method, headers: { cookie } });
        expect(response.status()).toBe(200);
        const headers = response.headers();
        expect(headers["x-frame-options"]).toBe("DENY");
        expect(headers["x-content-type-options"]).toBe("nosniff");
        expect(headers["permissions-policy"]).toBe(
          "camera=(), microphone=(), geolocation=(), payment=()",
        );
        expect(headers["cache-control"]).toBe("private, no-store");
        expect(headers["referrer-policy"]).toBe("no-referrer");
        // Preserve framework-managed content negotiation; do not infer Proxy
        // execution from the Edge-only middleware manifest or a Cookie Vary token.
        expect(headers.vary.toLowerCase().split(/,\s*/)).toContain("rsc");
      }
    });
  }
}

test("static assets remain outside the display response policy", async ({ request }) => {
  const response = await request.get("/favicon.ico");
  expect(response.status()).toBe(200);
  expect(response.headers()["referrer-policy"]).toBeUndefined();
  expect(response.headers()["x-frame-options"]).toBe("DENY");
  expect(response.headers()["x-content-type-options"]).toBe("nosniff");
});


test("security headers preserve the login UI and deny browser features", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "medi-chat にログイン" })).toBeVisible();
  const input = page.getByLabel("ログインID");
  await input.fill("header-smoke-user");
  await expect(input).toHaveValue("header-smoke-user");
  const allowed = await page.evaluate(() => {
    const policy = (document as Document & {
      featurePolicy: { allowsFeature(name: string): boolean };
    }).featurePolicy;
    return ["camera", "microphone", "geolocation", "payment"].map((feature) => policy.allowsFeature(feature));
  });
  expect(allowed).toEqual([false, false, false, false]);
});

test("browser refuses to render the app inside an iframe", async ({ page, baseURL }) => {
  const blocked = page.waitForEvent("console", {
    predicate: (message) => message.type() === "error" && /X-Frame-Options/i.test(message.text()),
  });
  await page.setContent(`<iframe src="${baseURL}/login"></iframe>`);
  await blocked;
  await expect(page.locator("iframe")).toHaveCount(1);
  expect(page.frames().some((frame) => frame.url() === `${baseURL}/login`)).toBe(false);
});
