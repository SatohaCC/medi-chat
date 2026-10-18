import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test } from "@playwright/test";
import type { SourceItem } from "../features/chat/model/chat";
import { openChat } from "./helpers/chat";

const projectRoot = resolve(__dirname, "../..");
const python = resolve(
  __dirname,
  process.platform === "win32"
    ? "../../backend/.venv/Scripts/python.exe"
    : "../../backend/.venv/bin/python",
);
const sources: SourceItem[] = process.env.MEDI_CHAT_EVIDENCE_FIXTURE
  ? JSON.parse(readFileSync(process.env.MEDI_CHAT_EVIDENCE_FIXTURE, "utf8"))
  : JSON.parse(
      execFileSync(python, ["-m", "backend.tests.support.registered_evidence_fixture"], {
        cwd: projectRoot,
        encoding: "utf8",
        env: { ...process.env, PYTHONIOENCODING: "utf-8", PYTHON_DOTENV_DISABLED: "1" },
      }),
    );

for (const width of [1280, 390]) {
  test(`現行登録形式の併用禁忌に列名と本文が表示される (${width}px)`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 1000 });
    const chat = await openChat(page);
    await chat.input.fill("併用禁忌の記載を確認");
    await chat.send.click();
    chat.respond({ type: "sources", sources });
    chat.respond({ type: "text_delta", content: "根拠を確認してください。" });
    chat.respond({ type: "text_done" });
    await page.getByRole("button", { name: /添付文書の根拠を表示/ }).click();
    const evidence = page.getByRole("complementary");
    const cards = evidence.locator('[data-evidence-design="InteractionEvidence"]');
    await expect(cards).toHaveCount(2);
    for (let index = 0; index < 2; index++) {
      for (const title of ["薬剤名", "臨床症状・措置方法", "機序・危険因子"]) {
        const headings = cards
          .nth(index)
          .getByRole("columnheader", { name: new RegExp(`^${title}`) });
        expect(await headings.count()).toBeGreaterThan(0);
        for (const heading of await headings.all()) await expect(heading).toBeVisible();
      }
    }
    await expect(
      evidence.getByRole("cell", { name: /アルコール/ }).first(),
    ).toBeVisible();
    await expect(
      evidence.getByRole("cell", { name: /リトナビル/ }).first(),
    ).toBeVisible();
    await page.screenshot({
      path: `../tmp/registered-evidence-${width}.png`,
      fullPage: true,
    });
  });
}
