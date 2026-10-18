import { expect, test } from "@playwright/test";
import { openChat } from "./helpers/chat";
import { visualSource } from "./helpers/presentation";

test("medicine names stay unmarked in evidence while clinical query terms highlight", async ({
  page,
}) => {
  const chat = await openChat(page);
  await chat.input.fill("テスト医薬品Aとテスト成分の出血・併用禁忌について");
  await chat.send.click();
  chat.respond({
    type: "sources",
    sources: [
      {
        ...visualSource,
        section: { code: "10.1", title: "併用禁忌" },
        excerpt: "テスト医薬品A（テスト成分）による出血の注意。",
      },
    ],
  });
  chat.respond({ type: "text_delta", content: "テスト回答" });
  chat.respond({ type: "text_done" });
  await page.getByRole("button", { name: /添付文書の根拠を表示/ }).click();
  const evidence = page.getByRole("complementary");
  await expect(evidence.locator("mark", { hasText: "出血" }).first()).toBeVisible();
  await expect(evidence.locator("mark", { hasText: "併用禁忌" }).first()).toBeVisible();
  await expect(evidence.locator("mark", { hasText: /テスト|医薬品|成分/ })).toHaveCount(
    0,
  );
  // Historical evidence must retain this behavior after the prescription changes.
  await page
    .getByTestId("tier-1-prescription")
    .getByRole("button", { name: "全解除", exact: true })
    .click();
  await expect(evidence.locator("mark", { hasText: /テスト|医薬品|成分/ })).toHaveCount(
    0,
  );
  await expect(evidence.locator("mark", { hasText: "出血" }).first()).toBeVisible();
});
