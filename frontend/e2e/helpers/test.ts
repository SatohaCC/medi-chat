import { test as base } from "@playwright/test";

export type { Page, TestInfo, WebSocketRoute } from "@playwright/test";
export { expect } from "@playwright/test";

/** Business UI regressions use an explicit authenticated actor; auth tests use their own API setup. */
export const test = base.extend({
  context: async ({ context }, use) => {
    await context.route("**/api/auth/me", (route) =>
      route.fulfill({
        json: {
          user_id: "test-user",
          expires_at: Math.floor(Date.now() / 1000) + 1800,
        },
      }),
    );
    await use(context);
  },
});
