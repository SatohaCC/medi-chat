import { expect, test } from "@playwright/test";
import type { SourceItem } from "../features/chat/model/chat";
import { openChat } from "./helpers/chat";

test("続きを読む includes citation and references in the same card region", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 900 });
  const chat = await openChat(page);
  await chat.input.fill("テスト根拠");
  await chat.send.click();
  chat.respond({
    type: "sources",
    sources: [
      {
        unit_id: "references-clamp",
        document_id: "test-document",
        product_name: "テスト医薬品",
        generic_name: "テスト成分",
        product_yj_codes: ["3339003F5020"],
        document_revision: { year_month: "2026-10", version: "第2版" },
        section: { code: "10", title: "相互作用" },
        kind: "section",
        excerpt: "短い原文です。",
        columns: null,
        references: Array.from({ length: 30 }, (_, index) => ({
          kind: "HeaderRef",
          target_section_code: `16.${index + 1}`,
          target_url: `https://example.invalid/reference/${index + 1}`,
        })),
        url: "https://example.invalid/source",
        retrieved_by: ["logic"],
      },
    ],
  });
  await page.getByRole("button", { name: /添付文書の根拠を表示/ }).click();
  const card = page.locator('[data-unit-id="references-clamp"]');
  const toggle = card.getByRole("button", { name: "続きを読む", exact: true });
  await expect(toggle).toBeVisible();
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  const regionId = await toggle.getAttribute("aria-controls");
  const region = card.locator(`[id="${regionId}"]`);
  const lastReference = region.locator('a[href="https://example.invalid/reference/30"]');
  await expect(lastReference).toHaveAttribute("tabindex", "-1");
  expect(
    await region.evaluate((element) => element.getBoundingClientRect().height),
  ).toBeLessThanOrEqual(150);
  await expect(region.getByText("改訂: 2026-10 / 第2版", { exact: true })).toHaveCount(1);
  await toggle.click();
  await expect(
    card.getByRole("button", { name: "折りたたむ", exact: true }),
  ).toHaveAttribute("aria-expanded", "true");
  await expect(lastReference).not.toHaveAttribute("tabindex", "-1");
  await expect(region.getByRole("link", { name: /PMDAの出典を開く/ })).toBeVisible();
  expect(
    await region.evaluate((element) => element.getBoundingClientRect().height),
  ).toBeGreaterThan(150);
  await card.getByRole("button", { name: "折りたたむ", exact: true }).click();
  await expect(lastReference).toHaveAttribute("tabindex", "-1");
  await page.screenshot({ path: "../tmp/evidence-card-collapsed.png", fullPage: true });
});

for (const width of [1280, 390]) {
  test(`根拠デザインは回答と分離し原文・出典を保持する (${width}px)`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    const chat = await openChat(page);
    await chat.input.fill("原文を確認したい");
    await chat.send.click();
    await expect.poll(() => chat.requests.length).toBe(1);
    expect(chat.requests[0]).not.toHaveProperty("enable_genui");
    const base: SourceItem = {
      unit_id: "interaction",
      document_id: "doc",
      product_name: "テスト医薬品A",
      generic_name: "テスト成分",
      product_yj_codes: ["3339003F5020"],
      document_revision: { year_month: "2026-10", version: "第2版" },
      section: { code: "10.1", title: "併用禁忌" },
      kind: "interaction_row",
      columns: {
        drug_name: "原文の相手薬",
        clinical_symptoms_and_measures: "原文の措置",
        mechanism_and_risk_factors: "原文の機序",
      },
      excerpt: "注）原文の条件を確認すること。",
      references: [],
      url: "https://example.invalid/source",
      retrieved_by: ["jev"],
    };
    const dosage: SourceItem = {
      ...base,
      unit_id: "dosage",
      section: { code: "6", title: "用法及び用量" },
      kind: "section",
      columns: null,
      excerpt:
        "| 対象 | 用量 |\n| --- | --- |\n| 成人 | 原文の用量 |\n\n注）原文の例外。",
    };
    chat.respond({ type: "sources", sources: [base] });
    chat.respond({ type: "text_delta", content: "**回答本文**" });
    await page.getByRole("button", { name: /添付文書の根拠を表示/ }).click();
    const evidence = page.getByRole("complementary");
    await expect(
      evidence.locator('[data-evidence-design="InteractionEvidence"]'),
    ).toBeVisible();
    await expect(evidence.getByText("原文の相手薬", { exact: true })).toBeVisible();
    for (const name of ["薬剤名等", "臨床症状・措置方法", "機序・危険因子"]) {
      await expect(
        evidence.getByRole("columnheader", { name, exact: true }),
      ).toBeVisible();
    }
    await evidence.getByText("注記・全文を表示", { exact: true }).click();
    // A progressive source update must add the next design without changing the answer.
    chat.respond({ type: "sources", sources: [base, dosage] });
    chat.respond({ type: "text_delta", content: "を継続します。" });
    chat.respond({ type: "retrieval_status", stage: "complete" });
    chat.respond({ type: "text_done" });
    await expect(
      evidence.locator('[data-evidence-design="DosageEvidence"]'),
    ).toBeVisible();
    await expect(
      evidence.getByRole("cell", { name: "原文の用量", exact: true }),
    ).toBeVisible();
    await expect(
      evidence.getByText("注）原文の条件を確認すること。", { exact: true }),
    ).toBeVisible();
    await expect(
      evidence.getByText("改訂: 2026-10 / 第2版", { exact: true }),
    ).toHaveCount(2);
    await expect(
      evidence.locator('a[href="https://example.invalid/source"]'),
    ).toHaveCount(2);
    const answer = page.locator(
      '[data-message-role="assistant"] [data-message-bubble="true"]',
    );
    await expect(answer.locator("strong")).toHaveText("回答本文");
    await expect(answer.locator("[data-evidence-design]")).toHaveCount(0);
    await expect(page.getByText("代替薬候補", { exact: false })).toHaveCount(0);
    await page.screenshot({
      path: `../tmp/source-evidence-${width}.png`,
      fullPage: true,
    });
  });
}
