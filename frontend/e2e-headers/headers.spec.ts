import { expect, test } from "@playwright/test";

for (const path of ["/", "/login", "/imports", "/search", "/guide"]) {
  for (const cookie of ["", "medi_chat_access_token=test-token"]) {
    test(`${path} keeps production response policy with ${cookie ? "a cookie" : "no cookie"}`, async ({ request }) => {
      for (const method of ["GET", "HEAD"]) {
        const response = await request.fetch(path, { method, headers: { cookie } });
        expect(response.status()).toBe(200);
        const headers = response.headers();
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
});
